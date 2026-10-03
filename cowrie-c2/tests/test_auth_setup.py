import os
import tempfile
import unittest

import database


class AuthSetupTests(unittest.TestCase):
    def setUp(self):
        self.original_db_path = database.DB_PATH
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        database.DB_PATH = self.temp_db.name
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self.original_db_path
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_hash_and_verify_password(self):
        salt, password_hash = database.hash_password("Password123!")

        self.assertTrue(database.verify_password("Password123!", password_hash, salt))
        self.assertFalse(database.verify_password("WrongPassword123!", password_hash, salt))
        self.assertGreaterEqual(len("Password123!"), 12)

    def test_create_user_requires_single_user_and_match(self):
        self.assertTrue(database.create_user("admin", "Password123!", "Password123!"))
        self.assertEqual(database.get_user_count(), 1)
        self.assertFalse(database.create_user("second", "Password123!", "Password123!"))

    def test_multiple_session_tokens_are_supported(self):
        self.assertTrue(database.create_user("admin", "Password123!", "Password123!"))

        first_token = database.create_session("admin")
        second_token = database.create_session("admin")

        self.assertIsNotNone(first_token)
        self.assertIsNotNone(second_token)
        self.assertNotEqual(first_token, second_token)

        user = database.get_user_from_session_tokens([first_token, second_token])
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], "admin")

        self.assertEqual(database.parse_session_cookie_value(f"{first_token}, {second_token}"), [first_token, second_token])


if __name__ == "__main__":
    unittest.main()
