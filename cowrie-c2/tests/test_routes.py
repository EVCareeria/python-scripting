import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import cowrie_telemetry
import database
from helpers import TEST_PASSWORD, TEST_USERNAME, AppTestCase

ROOT = Path(__file__).resolve().parent.parent


class RouteTestCase(AppTestCase):
    """Stubs out the telemetry sources so routes never touch real logs or run host commands."""

    def setUp(self):
        super().setUp()
        self.mock_suricata = self.patch_app("get_suricata_alerts", return_value=[])
        self.mock_cowrie_logs = self.patch_app("get_cowrie_digested_logs", return_value=[])
        self.mock_cowrie_files = self.patch_app("list_cowrie_log_files", return_value=[])
        self.mock_cowrie_file = self.patch_app("get_specific_cowrie_log", return_value=[])
        self.mock_host_command = self.patch_app("run_host_command", return_value="stubbed output")

    def patch_app(self, name, **kwargs):
        patcher = mock.patch.object(self.app_module, name, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def protected_paths(self):
        """One concrete URL for every registered route that should require a login."""
        paths = []
        for rule in self.app.url_map.iter_rules():
            if rule.endpoint == "static" or rule.rule in self.app_module.PUBLIC_ROUTES:
                continue
            path = rule.rule
            for argument in rule.arguments:
                path = re.sub(r"<(?:[^:<>]+:)?%s>" % re.escape(argument), "placeholder", path)
            paths.append(path)
        return paths

    def assert_redirects_to(self, response, path):
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], path)


class FirstRunTests(RouteTestCase):
    def test_everything_redirects_to_setup_until_a_user_exists(self):
        for path in self.protected_paths() + ["/login"]:
            with self.subTest(path=path):
                self.assert_redirects_to(self.client.get(path), "/setup")
        self.mock_host_command.assert_not_called()

    def test_setup_page_renders(self):
        response = self.client.get("/setup")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"confirm_password", response.data)

    def test_setup_rejects_invalid_input(self):
        cases = [
            ({"username": "  ", "password": TEST_PASSWORD, "confirm_password": TEST_PASSWORD}, b"Username is required."),
            ({"username": "admin", "password": "short", "confirm_password": "short"}, b"at least 12 characters"),
            ({"username": "admin", "password": TEST_PASSWORD, "confirm_password": "Different123!"}, b"Passwords do not match."),
            ({}, b"Username is required."),
        ]
        for form, message in cases:
            with self.subTest(form=form):
                response = self.client.post("/setup", data=form)

                self.assertEqual(response.status_code, 200)
                self.assertIn(message, response.data)
                self.assertIsNone(self.session_cookie())
        self.assertEqual(database.get_user_count(), 0)

    def test_setup_creates_the_user_and_logs_them_in(self):
        response = self.client.post("/setup", data={
            "username": TEST_USERNAME, "password": TEST_PASSWORD, "confirm_password": TEST_PASSWORD,
        })

        self.assert_redirects_to(response, "/dashboard")
        self.assertEqual(database.get_user_count(), 1)
        self.assertEqual(database.get_active_sessions_for_user(TEST_USERNAME), [self.session_cookie().value])
        self.assertEqual(self.client.get("/dashboard").status_code, 200)


class SetupLockoutTests(RouteTestCase):
    def setUp(self):
        super().setUp()
        self.create_test_user()

    def test_setup_page_is_closed_once_a_user_exists(self):
        self.assert_redirects_to(self.client.get("/setup"), "/login")

    def test_setup_cannot_create_or_replace_a_user_once_one_exists(self):
        response = self.client.post("/setup", data={
            "username": "attacker", "password": "AttackerPass123!", "confirm_password": "AttackerPass123!",
        })

        self.assert_redirects_to(response, "/login")
        self.assertIsNone(self.session_cookie())
        self.assertEqual(database.get_user_count(), 1)
        self.assertIsNone(database.get_user_by_username("attacker"))
        self.assertTrue(database.authenticate_user(TEST_USERNAME, TEST_PASSWORD))


class AuthEnforcementTests(RouteTestCase):
    def setUp(self):
        super().setUp()
        self.create_test_user()

    def test_every_protected_route_redirects_anonymous_visitors_to_login(self):
        paths = self.protected_paths()
        self.assertIn("/dashboard", paths)
        self.assertIn("/api/host/placeholder", paths)

        for path in paths:
            with self.subTest(path=path):
                self.assert_redirects_to(self.client.get(path), "/login")

    def test_anonymous_requests_never_reach_the_telemetry_sources(self):
        for path in self.protected_paths():
            self.client.get(path)

        for stub in (self.mock_suricata, self.mock_cowrie_logs, self.mock_cowrie_files,
                     self.mock_cowrie_file, self.mock_host_command):
            stub.assert_not_called()

    def test_forged_cookies_are_rejected(self):
        forged_values = ["", "garbage", "' OR '1'='1", ",,,", TEST_USERNAME, "a" * 43]
        for value in forged_values:
            with self.subTest(value=value):
                self.client.set_cookie(database.SESSION_COOKIE_NAME, value)

                self.assert_redirects_to(self.client.get("/dashboard"), "/login")

    def test_unknown_routes_also_require_a_login(self):
        self.assert_redirects_to(self.client.get("/api/does-not-exist"), "/login")

    def test_static_assets_do_not_require_a_login(self):
        response = self.client.get("/static/css/style.css")

        self.assertEqual(response.status_code, 200)
        response.close()

    def test_login_page_is_reachable(self):
        response = self.client.get("/login")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"password", response.data)


class LoginTests(RouteTestCase):
    def setUp(self):
        super().setUp()
        self.create_test_user()

    def test_bad_credentials_show_one_generic_error_and_set_no_cookie(self):
        attempts = [
            (TEST_USERNAME, "WrongPassword123!"),
            (TEST_USERNAME, ""),
            ("nobody", TEST_PASSWORD),
            ("' OR '1'='1", "' OR '1'='1"),
        ]
        for username, password in attempts:
            with self.subTest(username=username, password=password):
                response = self.login(username=username, password=password)

                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Invalid username or password.", response.data)
                self.assertIsNone(self.session_cookie())
        self.assertEqual(database.get_active_sessions_for_user(TEST_USERNAME), [])

    def test_successful_login_sets_a_session_cookie_and_grants_access(self):
        response = self.login()

        self.assert_redirects_to(response, "/dashboard")
        token = self.session_cookie().value
        self.assertEqual(database.get_active_sessions_for_user(TEST_USERNAME), [token])
        self.assertEqual(self.client.get("/dashboard").status_code, 200)

    def test_session_cookie_attributes(self):
        header = self.login().headers["Set-Cookie"]

        self.assertTrue(header.startswith(database.SESSION_COOKIE_NAME + "="))
        self.assertIn("HttpOnly", header)
        self.assertIn("SameSite=Lax", header)
        self.assertIn("Path=/", header)
        self.assertIn("Max-Age=43200", header)

    def test_cookie_does_not_contain_the_credentials(self):
        self.login()

        value = self.session_cookie().value
        self.assertNotIn(TEST_USERNAME, value)
        self.assertNotIn(TEST_PASSWORD, value)

    def test_each_login_gets_its_own_token(self):
        other_client = self.app.test_client()
        self.login()
        self.login(client=other_client)

        first = self.session_cookie().value
        second = self.session_cookie(other_client).value
        self.assertNotEqual(first, second)
        self.assertCountEqual(database.get_active_sessions_for_user(TEST_USERNAME), [first, second])

    def test_logging_in_again_keeps_the_existing_token_in_the_cookie(self):
        self.login()
        first = self.session_cookie().value
        self.login()
        second = next(t for t in database.get_active_sessions_for_user(TEST_USERNAME) if t != first)

        # The cookie now carries both tokens, so revoking the newer one must not log the browser out.
        database.delete_session_token(second)

        self.assertEqual(self.client.get("/dashboard").status_code, 200)

    def test_username_is_stripped_before_authenticating(self):
        self.assert_redirects_to(self.login(username=f"  {TEST_USERNAME}  "), "/dashboard")


class LogoutTests(RouteTestCase):
    def setUp(self):
        super().setUp()
        self.create_test_user()
        self.login()
        self.token = self.session_cookie().value

    def test_logout_clears_the_cookie_and_revokes_the_token(self):
        response = self.client.get("/logout")

        self.assert_redirects_to(response, "/login")
        self.assertIsNone(self.session_cookie())
        self.assertIsNone(database.get_user_from_session_tokens([self.token]))
        self.assert_redirects_to(self.client.get("/dashboard"), "/login")

    def test_a_stolen_cookie_stops_working_after_logout(self):
        thief = self.app.test_client()
        thief.set_cookie(database.SESSION_COOKIE_NAME, self.token)
        self.assertEqual(thief.get("/dashboard").status_code, 200)

        self.client.get("/logout")

        self.assert_redirects_to(thief.get("/dashboard"), "/login")

    def test_logout_without_a_session_is_harmless(self):
        anonymous = self.app.test_client()

        self.assert_redirects_to(anonymous.get("/logout"), "/login")
        self.assertIsNotNone(database.get_user_from_session_tokens([self.token]))


class AuthenticatedPageTests(RouteTestCase):
    def setUp(self):
        super().setUp()
        self.create_test_user()
        self.login()

    def test_dashboard_asks_for_the_expected_amount_of_data(self):
        self.assertEqual(self.client.get("/dashboard").status_code, 200)

        self.mock_suricata.assert_called_once_with(limit=25)
        self.mock_cowrie_logs.assert_called_once_with(limit=50)

    def test_dashboard_shows_suricata_alerts(self):
        self.mock_suricata.return_value = [
            {"timestamp": "2026-10-04T12:00:00", "src_ip": "203.0.113.5", "signature": "ET SCAN Potential SSH Scan"},
        ]

        html = self.client.get("/dashboard").get_data(as_text=True)

        self.assertIn("203.0.113.5", html)
        self.assertIn("ET SCAN Potential SSH Scan", html)
        self.assertNotIn("No Suricata alerts recorded yet.", html)

    def test_dashboard_without_alerts_shows_the_empty_state(self):
        self.assertIn("No Suricata alerts recorded yet.", self.client.get("/dashboard").get_data(as_text=True))

    def test_dashboard_escapes_html_in_alert_fields(self):
        payload = "<script>alert('xss')</script>"
        self.mock_suricata.return_value = [{"timestamp": payload, "src_ip": payload, "signature": payload}]

        html = self.client.get("/dashboard").get_data(as_text=True)

        self.assertNotIn(payload, html)
        self.assertIn("&lt;script&gt;", html)

    def test_host_page_renders(self):
        self.assertEqual(self.client.get("/host").status_code, 200)


class AuthenticatedApiTests(RouteTestCase):
    def setUp(self):
        super().setUp()
        self.create_test_user()
        self.login()

    def test_host_command_api_returns_the_command_output(self):
        response = self.client.get("/api/host/docker_ps")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"command": "docker_ps", "output": "stubbed output"})
        self.mock_host_command.assert_called_once_with("docker_ps")

    def test_host_command_api_only_accepts_get(self):
        self.assertEqual(self.client.post("/api/host/docker_ps").status_code, 405)
        self.mock_host_command.assert_not_called()

    def test_cowrie_stream_api(self):
        self.mock_cowrie_logs.return_value = [{"session": "aaa", "commands": ["uname -a"]}]

        response = self.client.get("/api/cowrie/stream")

        self.assertEqual(response.get_json(), [{"session": "aaa", "commands": ["uname -a"]}])
        self.mock_cowrie_logs.assert_called_once_with(limit=50)

    def test_cowrie_stream_api_returns_attacker_input_as_json_not_html(self):
        payload = "<script>alert(1)</script>"
        self.mock_cowrie_logs.return_value = [{"session": "aaa", "commands": [payload]}]

        response = self.client.get("/api/cowrie/stream")

        self.assertEqual(response.mimetype, "application/json")
        self.assertEqual(json.loads(response.data)[0]["commands"], [payload])

    def test_suricata_alerts_api(self):
        alerts = [{"timestamp": "2026-10-04T12:00:00", "src_ip": "203.0.113.5", "signature": "ET SCAN"}]
        self.mock_suricata.return_value = alerts

        response = self.client.get("/api/suricata/alerts")

        self.assertEqual(response.get_json(), alerts)
        self.mock_suricata.assert_called_once_with(limit=25)

    def test_cowrie_files_api(self):
        self.mock_cowrie_files.return_value = [{"filename": "cowrie.json.2026-10-03", "size": 20}]

        self.assertEqual(self.client.get("/api/cowrie/files").get_json(),
                         [{"filename": "cowrie.json.2026-10-03", "size": 20}])

    def test_cowrie_file_api_passes_the_filename_through(self):
        self.mock_cowrie_file.return_value = [{"session": "old"}]

        response = self.client.get("/api/cowrie/file/cowrie.json.2026-10-03")

        self.assertEqual(response.get_json(), [{"session": "old"}])
        self.mock_cowrie_file.assert_called_once_with("cowrie.json.2026-10-03", limit=100)


class UnstubbedIntegrationTests(AppTestCase):
    """Routes wired to the real telemetry modules, with only the outside world faked."""

    def setUp(self):
        super().setUp()
        self.create_test_user()
        self.login()

    def test_host_command_api_refuses_commands_outside_the_whitelist(self):
        with mock.patch("host_telemetry.subprocess.run") as mock_run:
            for cmd_type in ("id", "W", "w;id", "$(reboot)", "docker_ps -a"):
                with self.subTest(cmd_type=cmd_type):
                    response = self.client.get(f"/api/host/{cmd_type}")

                    self.assertEqual(response.get_json()["output"], "Error: Command not allowed.")
        mock_run.assert_not_called()

    def test_cowrie_file_api_cannot_read_outside_the_log_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = os.path.join(temp_dir, "logs")
            os.mkdir(log_dir)
            with open(os.path.join(temp_dir, "outside.json"), "w", encoding="utf-8") as f:
                f.write(json.dumps({"session": "outside", "timestamp": "t1"}) + "\n")

            with mock.patch.object(cowrie_telemetry, "LOG_FILE_PATH", os.path.join(log_dir, "cowrie.json")):
                for path in ("/api/cowrie/file/../outside.json", "/api/cowrie/file/..%2Foutside.json"):
                    with self.subTest(path=path):
                        response = self.client.get(path)

                        self.assertNotIn(b"outside", response.data)

    def test_every_api_path_used_by_the_frontend_exists(self):
        sources = [ROOT / "static/js/dashboard.js", ROOT / "templates/host.html", ROOT / "templates/dashboard.html"]
        api_paths = set()
        for source in sources:
            for path in re.findall(r"""fetch\(\s*['"`](/api/[^'"`]*)""", source.read_text()):
                api_paths.add(re.sub(r"\$\{[^}]*\}", "placeholder", path))
        self.assertTrue(api_paths)

        with mock.patch("host_telemetry.subprocess.run", return_value=mock.Mock(returncode=0, stdout="ok")):
            for path in sorted(api_paths):
                with self.subTest(path=path):
                    self.assertEqual(self.client.get(path).status_code, 200)


if __name__ == "__main__":
    unittest.main()
