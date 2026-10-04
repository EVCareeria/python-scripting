import os
import subprocess
import tempfile
import unittest
from unittest import mock

import host_telemetry

EXPECTED_COMMANDS = {
    "w": ["w"],
    "last": ["last", "-n", "10"],
    "fail2ban_status": ["sudo", "fail2ban-client", "status"],
    "fail2ban_sshd": ["sudo", "fail2ban-client", "status", "sshd"],
    "docker_ps": ["docker", "ps"],
}


def completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class RunHostCommandTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(host_telemetry.subprocess, "run", return_value=completed(stdout="ok\n"))
        self.mock_run = patcher.start()
        self.addCleanup(patcher.stop)

    def test_commands_outside_the_whitelist_never_reach_subprocess(self):
        rejected = [
            "", "id", "rm", "W", "w ", "w; id", "w && id", "w|id", "$(id)", "`id`",
            "../w", "docker_ps -a", "docker", "sudo", "fail2ban_status;reboot",
        ]
        for cmd_type in rejected:
            with self.subTest(cmd_type=cmd_type):
                self.assertEqual(host_telemetry.run_host_command(cmd_type), "Error: Command not allowed.")
        self.mock_run.assert_not_called()

    def test_whitelisted_commands_run_a_fixed_argv_without_a_shell(self):
        for cmd_type, argv in EXPECTED_COMMANDS.items():
            with self.subTest(cmd_type=cmd_type):
                self.mock_run.reset_mock()

                self.assertEqual(host_telemetry.run_host_command(cmd_type), "ok\n")

                self.mock_run.assert_called_once()
                args, kwargs = self.mock_run.call_args
                self.assertEqual(args, (argv,))
                self.assertFalse(kwargs.get("shell", False))
                self.assertEqual(kwargs.get("timeout"), 3)

    def test_empty_stdout_gets_a_placeholder(self):
        self.mock_run.return_value = completed(stdout="")

        self.assertEqual(host_telemetry.run_host_command("w"), "Command executed successfully with no output.")

    def test_non_zero_exit_reports_code_and_stderr(self):
        self.mock_run.return_value = completed(returncode=1, stdout="ignored", stderr="  permission denied\n")

        self.assertEqual(host_telemetry.run_host_command("docker_ps"), "Error (Exit 1): permission denied")

    def test_timeout_is_reported(self):
        self.mock_run.side_effect = subprocess.TimeoutExpired(cmd=["w"], timeout=3)

        self.assertEqual(host_telemetry.run_host_command("w"), "Error: Command timed out.")

    def test_missing_binary_is_reported_instead_of_raised(self):
        self.mock_run.side_effect = FileNotFoundError("No such file or directory: 'docker'")

        self.assertTrue(host_telemetry.run_host_command("docker_ps").startswith("Exception: "))

    def test_fail2ban_logs_reads_the_log_file_instead_of_running_a_command(self):
        with mock.patch.object(host_telemetry, "read_log_lines", return_value=["one", "two"]) as mock_read:
            self.assertEqual(host_telemetry.run_host_command("fail2ban_logs"), "one\ntwo")

        mock_read.assert_called_once_with("/var/log/fail2ban.log", 30)
        self.mock_run.assert_not_called()

    def test_fail2ban_logs_without_a_log_file(self):
        with mock.patch.object(host_telemetry, "read_log_lines", return_value=[]):
            self.assertEqual(
                host_telemetry.run_host_command("fail2ban_logs"),
                "No Fail2Ban log found at /var/log/fail2ban.log.",
            )


class ReadLogLinesTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.log_path = os.path.join(self.temp_dir.name, "fail2ban.log")

    def test_missing_file_gives_no_lines(self):
        self.assertEqual(host_telemetry.read_log_lines(self.log_path), [])

    def test_returns_the_last_n_lines_stripped(self):
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write("".join(f"  line {i}  \n" for i in range(10)))

        self.assertEqual(host_telemetry.read_log_lines(self.log_path, 3), ["line 7", "line 8", "line 9"])

    def test_invalid_utf8_does_not_raise(self):
        with open(self.log_path, "wb") as f:
            f.write(b"good line\n\xff\xfe broken\n")

        lines = host_telemetry.read_log_lines(self.log_path)
        self.assertEqual(lines[0], "good line")
        self.assertEqual(len(lines), 2)

    def test_unreadable_path_gives_no_lines(self):
        self.assertEqual(host_telemetry.read_log_lines(self.temp_dir.name), [])


if __name__ == "__main__":
    unittest.main()
