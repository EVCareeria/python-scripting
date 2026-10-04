import os
import sqlite3
import tempfile
import unittest

import database
from helpers import TEST_PASSWORD, TEST_USERNAME, TempDatabaseTestCase


class PasswordHashingTests(TempDatabaseTestCase):
    def test_same_password_gets_a_different_salt_and_hash_each_time(self):
        first_salt, first_hash = database.hash_password(TEST_PASSWORD)
        second_salt, second_hash = database.hash_password(TEST_PASSWORD)

        self.assertNotEqual(first_salt, second_salt)
        self.assertNotEqual(first_hash, second_hash)

    def test_verify_rejects_the_right_password_with_the_wrong_salt(self):
        _, password_hash = database.hash_password(TEST_PASSWORD)
        other_salt, _ = database.hash_password(TEST_PASSWORD)

        self.assertFalse(database.verify_password(TEST_PASSWORD, password_hash, other_salt))

    def test_unicode_passwords_round_trip(self):
        password = "pässwörd-with-ünicode-🔒"
        salt, password_hash = database.hash_password(password)

        self.assertTrue(database.verify_password(password, password_hash, salt))

    def test_password_is_not_stored_in_plaintext(self):
        self.create_test_user()

        user = database.get_user_by_username(TEST_USERNAME)
        self.assertNotIn(TEST_PASSWORD, user["password_hash"])
        self.assertNotIn(TEST_PASSWORD, user["salt"])
        with open(database.DB_PATH, "rb") as f:
            self.assertNotIn(TEST_PASSWORD.encode(), f.read())


class CreateUserTests(TempDatabaseTestCase):
    def test_init_db_is_idempotent_and_keeps_existing_data(self):
        self.create_test_user()
        database.init_db()

        self.assertEqual(database.get_user_count(), 1)

    def test_rejects_missing_username(self):
        for username in ("", "   ", None):
            with self.subTest(username=username):
                self.assertFalse(database.create_user(username, TEST_PASSWORD, TEST_PASSWORD))
        self.assertEqual(database.get_user_count(), 0)

    def test_rejects_short_or_missing_password(self):
        for password in ("", None, "short", "elevenchars"):
            with self.subTest(password=password):
                self.assertFalse(database.create_user(TEST_USERNAME, password, password))
        self.assertEqual(database.get_user_count(), 0)

    def test_accepts_password_of_exactly_twelve_characters(self):
        self.assertTrue(database.create_user(TEST_USERNAME, "twelve-chars", "twelve-chars"))

    def test_rejects_mismatched_confirmation(self):
        self.assertFalse(database.create_user(TEST_USERNAME, TEST_PASSWORD, TEST_PASSWORD + "x"))
        self.assertEqual(database.get_user_count(), 0)

    def test_username_is_stripped(self):
        self.assertTrue(database.create_user("  admin  ", TEST_PASSWORD, TEST_PASSWORD))

        self.assertIsNotNone(database.get_user_by_username("admin"))


class AuthenticateUserTests(TempDatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.create_test_user()

    def test_accepts_correct_credentials(self):
        self.assertTrue(database.authenticate_user(TEST_USERNAME, TEST_PASSWORD))

    def test_rejects_wrong_password(self):
        for password in ("", "WrongPassword123!", TEST_PASSWORD + " ", TEST_PASSWORD.lower()):
            with self.subTest(password=password):
                self.assertFalse(database.authenticate_user(TEST_USERNAME, password))

    def test_rejects_unknown_or_differently_cased_username(self):
        for username in ("", "nobody", TEST_USERNAME.upper()):
            with self.subTest(username=username):
                self.assertFalse(database.authenticate_user(username, TEST_PASSWORD))

    def test_sql_injection_in_username_does_not_authenticate(self):
        for username in ("' OR '1'='1", "admin' --", "admin'; DROP TABLE app_users; --"):
            with self.subTest(username=username):
                self.assertFalse(database.authenticate_user(username, TEST_PASSWORD))
        self.assertEqual(database.get_user_count(), 1)


class SessionTests(TempDatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.create_test_user()

    def test_create_session_for_unknown_user_returns_none(self):
        self.assertIsNone(database.create_session("nobody"))
        self.assertEqual(database.get_active_sessions_for_user("nobody"), [])

    def test_session_tokens_are_long_and_unique(self):
        tokens = {database.build_session_token() for _ in range(100)}

        self.assertEqual(len(tokens), 100)
        self.assertTrue(all(len(token) >= 43 for token in tokens))

    def test_created_session_is_listed_as_active(self):
        token = database.create_session(TEST_USERNAME)

        self.assertEqual(database.get_active_sessions_for_user(TEST_USERNAME), [token])

    def test_lookup_with_no_or_unknown_tokens_returns_none(self):
        database.create_session(TEST_USERNAME)

        for tokens in ([], None, ["not-a-real-token"], [""]):
            with self.subTest(tokens=tokens):
                self.assertIsNone(database.get_user_from_session_tokens(tokens))

    def test_lookup_succeeds_when_one_of_several_tokens_is_valid(self):
        token = database.create_session(TEST_USERNAME)

        user = database.get_user_from_session_tokens(["stale-token", token])
        self.assertEqual(user["username"], TEST_USERNAME)

    def test_sql_injection_in_token_does_not_match_a_session(self):
        database.create_session(TEST_USERNAME)

        for token in ("' OR '1'='1", "x') OR 1=1 --", "'; DROP TABLE app_sessions; --"):
            with self.subTest(token=token):
                self.assertIsNone(database.get_user_from_session_tokens([token]))
        self.assertEqual(len(database.get_active_sessions_for_user(TEST_USERNAME)), 1)

    def test_delete_session_token_only_removes_that_token(self):
        first_token = database.create_session(TEST_USERNAME)
        second_token = database.create_session(TEST_USERNAME)

        database.delete_session_token(first_token)

        self.assertIsNone(database.get_user_from_session_tokens([first_token]))
        self.assertIsNotNone(database.get_user_from_session_tokens([second_token]))

    def test_delete_all_user_sessions(self):
        tokens = [database.create_session(TEST_USERNAME) for _ in range(3)]

        database.delete_all_user_sessions(TEST_USERNAME)

        self.assertEqual(database.get_active_sessions_for_user(TEST_USERNAME), [])
        self.assertIsNone(database.get_user_from_session_tokens(tokens))

    def test_delete_all_user_sessions_for_unknown_user_is_a_noop(self):
        token = database.create_session(TEST_USERNAME)

        database.delete_all_user_sessions("nobody")

        self.assertEqual(database.get_active_sessions_for_user(TEST_USERNAME), [token])


class ParseSessionCookieTests(unittest.TestCase):
    def test_empty_values_give_no_tokens(self):
        for raw_value in ("", None, "   ", ",", " , , "):
            with self.subTest(raw_value=raw_value):
                self.assertEqual(database.parse_session_cookie_value(raw_value), [])

    def test_tokens_are_stripped_and_deduplicated_in_order(self):
        self.assertEqual(database.parse_session_cookie_value(" b ,a,,b, c ,"), ["b", "a", "c"])


class AuditLogTests(TempDatabaseTestCase):
    def test_log_event_stores_details_verbatim(self):
        details = "'); DROP TABLE audit_logs; --"
        database.log_event("2026-10-04T12:00:00", "cowrie", details)

        conn = sqlite3.connect(database.DB_PATH)
        rows = conn.execute("SELECT timestamp, source, details FROM audit_logs").fetchall()
        conn.close()
        self.assertEqual(rows, [("2026-10-04T12:00:00", "cowrie", details)])

    def test_log_event_swallows_database_errors(self):
        database.DB_PATH = os.path.join(tempfile.gettempdir(), "missing-dir-for-cowrie-c2", "c2.db")

        database.log_event("2026-10-04T12:00:00", "cowrie", "details")


if __name__ == "__main__":
    unittest.main()
