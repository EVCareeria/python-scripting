import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

import cowrie_telemetry
import suricata_telemetry
from helpers import load_app_module


class StartupTestCase(unittest.TestCase):
    def setUp(self):
        self.app_module = load_app_module()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.cowrie_dir = os.path.join(self.temp_dir.name, "cowrie")
        self.suricata_dir = os.path.join(self.temp_dir.name, "suricata")
        os.mkdir(self.cowrie_dir)
        os.mkdir(self.suricata_dir)
        self.missing_dir = os.path.join(self.temp_dir.name, "missing")


class ResolveLogPathTests(StartupTestCase):
    def test_directory_gets_the_default_filename(self):
        self.assertEqual(
            self.app_module.resolve_log_path(self.cowrie_dir, "cowrie.json"),
            os.path.join(self.cowrie_dir, "cowrie.json"),
        )

    def test_file_path_is_kept(self):
        path = os.path.join(self.cowrie_dir, "custom.json")

        self.assertEqual(self.app_module.resolve_log_path(path, "cowrie.json"), path)

    def test_missing_path_without_a_json_name_is_treated_as_a_directory(self):
        self.assertEqual(
            self.app_module.resolve_log_path(self.missing_dir, "cowrie.json"),
            os.path.join(self.missing_dir, "cowrie.json"),
        )

    def test_relative_path_becomes_absolute(self):
        self.assertTrue(os.path.isabs(self.app_module.resolve_log_path("logs/cowrie.json", "cowrie.json")))


class CheckLogPathTests(StartupTestCase):
    def test_readable_directory_passes_even_before_the_log_file_exists(self):
        self.assertIsNone(self.app_module.check_log_path("Cowrie logs", os.path.join(self.cowrie_dir, "cowrie.json")))

    def test_missing_directory_is_reported(self):
        error = self.app_module.check_log_path("Cowrie logs", os.path.join(self.missing_dir, "cowrie.json"))

        self.assertIn("Cowrie logs: directory not found", error)
        self.assertIn(self.missing_dir, error)

    @unittest.skipIf(os.geteuid() == 0, "root can read everything")
    def test_unreadable_directory_is_reported(self):
        os.chmod(self.cowrie_dir, 0o000)
        self.addCleanup(os.chmod, self.cowrie_dir, 0o700)

        error = self.app_module.check_log_path("Cowrie logs", os.path.join(self.cowrie_dir, "cowrie.json"))

        self.assertIn("no permission to read directory", error)

    @unittest.skipIf(os.geteuid() == 0, "root can read everything")
    def test_unreadable_log_file_is_reported(self):
        path = os.path.join(self.suricata_dir, "eve.json")
        open(path, "w").close()
        os.chmod(path, 0o000)

        error = self.app_module.check_log_path("Suricata logs", path)

        self.assertIn("Suricata logs: no permission to read file", error)


class MainTests(StartupTestCase):
    def setUp(self):
        super().setUp()
        # main() repoints the telemetry modules; put them back after each test.
        for module, name in ((cowrie_telemetry, "LOG_FILE_PATH"), (suricata_telemetry, "EVE_LOG_PATH")):
            patcher = mock.patch.object(module, name, getattr(module, name))
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(self.app_module.app, "run")
        self.mock_run = patcher.start()
        self.addCleanup(patcher.stop)

    def run_main(self, *argv):
        """Run main() and return (exit_code, stderr); exit_code is None when the server was started."""
        stderr = io.StringIO()
        exit_code = None
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            try:
                self.app_module.main(list(argv))
            except SystemExit as exc:
                exit_code = exc.code
        return exit_code, stderr.getvalue()

    def test_starts_and_points_the_telemetry_modules_at_the_given_directories(self):
        exit_code, _ = self.run_main("--cowrie-logs", self.cowrie_dir, "--suricata-logs", self.suricata_dir)

        self.assertIsNone(exit_code)
        self.mock_run.assert_called_once()
        self.assertEqual(cowrie_telemetry.LOG_FILE_PATH, os.path.join(self.cowrie_dir, "cowrie.json"))
        self.assertEqual(suricata_telemetry.EVE_LOG_PATH, os.path.join(self.suricata_dir, "eve.json"))

    def test_configured_paths_are_what_the_telemetry_functions_read(self):
        with open(os.path.join(self.cowrie_dir, "cowrie.json"), "w", encoding="utf-8") as f:
            f.write('{"session": "aaa", "timestamp": "t1"}\n')
        with open(os.path.join(self.cowrie_dir, "cowrie.json.1"), "w", encoding="utf-8") as f:
            f.write('{"session": "old", "timestamp": "t0"}\n')
        with open(os.path.join(self.suricata_dir, "eve.json"), "w", encoding="utf-8") as f:
            f.write('{"event_type": "alert", "src_ip": "203.0.113.5"}\n')

        self.run_main("--cowrie-logs", self.cowrie_dir, "--suricata-logs", self.suricata_dir)

        self.assertEqual([s["session"] for s in cowrie_telemetry.get_cowrie_digested_logs()], ["aaa"])
        self.assertEqual([f["filename"] for f in cowrie_telemetry.list_cowrie_log_files()], ["cowrie.json.1"])
        self.assertEqual([s["session"] for s in cowrie_telemetry.get_specific_cowrie_log("cowrie.json.1")], ["old"])
        self.assertEqual([a["src_ip"] for a in suricata_telemetry.get_suricata_alerts()], ["203.0.113.5"])

    def test_file_paths_are_accepted_too(self):
        cowrie_file = os.path.join(self.cowrie_dir, "honeypot.json")

        exit_code, _ = self.run_main("--cowrie-logs", cowrie_file, "--suricata-logs", self.suricata_dir)

        self.assertIsNone(exit_code)
        self.assertEqual(cowrie_telemetry.LOG_FILE_PATH, cowrie_file)

    def test_refuses_to_start_when_a_directory_is_unreachable(self):
        original_cowrie_path = cowrie_telemetry.LOG_FILE_PATH
        cases = [
            (self.missing_dir, self.suricata_dir, ["Cowrie logs"]),
            (self.cowrie_dir, self.missing_dir, ["Suricata logs"]),
            (self.missing_dir, self.missing_dir, ["Cowrie logs", "Suricata logs"]),
        ]
        for cowrie, suricata, labels in cases:
            with self.subTest(labels=labels):
                exit_code, stderr = self.run_main("--cowrie-logs", cowrie, "--suricata-logs", suricata)

                self.assertEqual(exit_code, 1)
                for label in labels:
                    self.assertIn(f"Startup check failed - {label}", stderr)
        self.mock_run.assert_not_called()
        self.assertEqual(cowrie_telemetry.LOG_FILE_PATH, original_cowrie_path)

    def test_defaults_are_checked_when_no_arguments_are_given(self):
        cowrie_telemetry.LOG_FILE_PATH = os.path.join(self.missing_dir, "cowrie.json")
        suricata_telemetry.EVE_LOG_PATH = os.path.join(self.suricata_dir, "eve.json")

        exit_code, stderr = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertIn("Cowrie logs: directory not found", stderr)
        self.mock_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
