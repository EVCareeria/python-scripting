import os
import shutil
import tempfile
import unittest

import database

TEST_USERNAME = "admin"
TEST_PASSWORD = "Password123!"


def load_app_module():
    """Import app.py without letting its import-time init_db() create c2_data.db in the cwd."""
    original_db_path = database.DB_PATH
    scratch_dir = tempfile.mkdtemp()
    database.DB_PATH = os.path.join(scratch_dir, "import.db")
    try:
        import app as app_module
    finally:
        database.DB_PATH = original_db_path
        shutil.rmtree(scratch_dir, ignore_errors=True)
    return app_module


class TempDatabaseTestCase(unittest.TestCase):
    """Points the database module at a throwaway SQLite file for each test."""

    def setUp(self):
        self.original_db_path = database.DB_PATH
        self.original_iterations = database.PBKDF2_ITERATIONS
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        database.DB_PATH = self.temp_db.name
        # The real iteration count makes every create_user/login take ~100ms+ (far more on a Pi).
        database.PBKDF2_ITERATIONS = 1000
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self.original_db_path
        database.PBKDF2_ITERATIONS = self.original_iterations
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def create_test_user(self):
        self.assertTrue(database.create_user(TEST_USERNAME, TEST_PASSWORD, TEST_PASSWORD))


class AppTestCase(TempDatabaseTestCase):
    """Adds a Flask test client on top of the temporary database."""

    def setUp(self):
        super().setUp()
        self.app_module = load_app_module()
        self.app = self.app_module.app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def login(self, client=None, username=TEST_USERNAME, password=TEST_PASSWORD):
        client = client or self.client
        return client.post("/login", data={"username": username, "password": password})

    def session_cookie(self, client=None):
        client = client or self.client
        return client.get_cookie(database.SESSION_COOKIE_NAME)
