import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

import suricata_telemetry


def alert(n, **overrides):
    event = {
        "event_type": "alert",
        "timestamp": f"2026-10-04T12:00:{n:02d}",
        "src_ip": f"10.0.0.{n}",
        "alert": {"signature": f"ET SCAN signature {n}"},
    }
    event.update(overrides)
    return event


class EveLogTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.eve_path = os.path.join(self.temp_dir.name, "eve.json")
        patcher = mock.patch.object(suricata_telemetry, "EVE_LOG_PATH", self.eve_path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_eve(self, lines, trailing_newline=True):
        """Write lines to eve.json; dicts are JSON-encoded, strings are written as-is."""
        content = "\n".join(line if isinstance(line, str) else json.dumps(line) for line in lines)
        with open(self.eve_path, "w", encoding="utf-8") as f:
            f.write(content + ("\n" if trailing_newline and lines else ""))


class SuricataAlertsTests(EveLogTestCase):
    def test_missing_eve_file_gives_no_alerts(self):
        self.assertEqual(suricata_telemetry.get_suricata_alerts(), [])

    def test_empty_eve_file_gives_no_alerts(self):
        self.write_eve([])

        self.assertEqual(suricata_telemetry.get_suricata_alerts(), [])

    def test_unreadable_eve_file_gives_no_alerts_and_reports_why(self):
        os.mkdir(self.eve_path)
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            self.assertEqual(suricata_telemetry.get_suricata_alerts(), [])

        self.assertIn("Error reading Suricata logs", stdout.getvalue())

    def test_only_alert_events_are_returned(self):
        self.write_eve([
            {"event_type": "flow", "src_ip": "10.0.0.9"},
            alert(1),
            {"event_type": "dns", "src_ip": "10.0.0.9", "rrname": "alert.example.com"},
        ])

        self.assertEqual(suricata_telemetry.get_suricata_alerts(), [{
            "timestamp": "2026-10-04T12:00:01",
            "src_ip": "10.0.0.1",
            "signature": "ET SCAN signature 1",
        }])

    def test_alerts_are_newest_first_and_limited(self):
        self.write_eve([alert(n) for n in range(1, 6)])

        alerts = suricata_telemetry.get_suricata_alerts(limit=2)

        self.assertEqual([a["src_ip"] for a in alerts], ["10.0.0.5", "10.0.0.4"])

    def test_malformed_blank_and_non_object_lines_are_skipped(self):
        self.write_eve(["not json alert", "", '{"event_type": "alert", ', '"alert"', '["alert"]', alert(1)])

        self.assertEqual(len(suricata_telemetry.get_suricata_alerts()), 1)

    def test_last_line_without_a_trailing_newline_is_read(self):
        self.write_eve([alert(1), alert(2)], trailing_newline=False)

        self.assertEqual([a["src_ip"] for a in suricata_telemetry.get_suricata_alerts()], ["10.0.0.2", "10.0.0.1"])

    def test_invalid_utf8_does_not_hide_other_alerts(self):
        self.write_eve([alert(1)])
        with open(self.eve_path, "ab") as f:
            f.write(b'{"event_type": "alert", "src_ip": "\xff\xfe"}\n')

        self.assertEqual(len(suricata_telemetry.get_suricata_alerts()), 2)

    def test_missing_fields_become_empty_strings(self):
        self.write_eve([{"event_type": "alert"}])

        self.assertEqual(suricata_telemetry.get_suricata_alerts(), [{"timestamp": "", "src_ip": "", "signature": ""}])

    def test_non_string_fields_are_coerced_to_strings(self):
        self.write_eve([alert(1, timestamp=1234, src_ip=None, alert={"signature": ["a"]}), alert(2, alert="oops")])

        self.assertEqual(suricata_telemetry.get_suricata_alerts(), [
            {"timestamp": "2026-10-04T12:00:02", "src_ip": "10.0.0.2", "signature": ""},
            {"timestamp": "1234", "src_ip": "None", "signature": "['a']"},
        ])


class ReverseReadingTests(EveLogTestCase):
    def test_lines_come_back_last_to_first_across_chunk_boundaries(self):
        lines = [f"line-{n}-" + "x" * (n % 7) for n in range(200)]
        self.write_eve(lines)

        for chunk_bytes in (1, 3, 16, 1024):
            with self.subTest(chunk_bytes=chunk_bytes):
                read = [l.decode() for l in suricata_telemetry.iter_lines_reversed(self.eve_path, chunk_bytes=chunk_bytes)]

                self.assertEqual([l for l in read if l], lines[::-1])

    def test_alerts_spanning_many_chunks_are_all_found(self):
        self.write_eve([alert(n % 60, src_ip=f"10.0.{n // 250}.{n % 250}") for n in range(500)])

        with mock.patch.object(suricata_telemetry, "CHUNK_BYTES", 100):
            alerts = suricata_telemetry.get_suricata_alerts(limit=500)

        self.assertEqual(len(alerts), 500)
        self.assertEqual(alerts[0]["src_ip"], "10.0.1.249")
        self.assertEqual(alerts[-1]["src_ip"], "10.0.0.0")

    def test_only_the_end_of_a_large_file_is_read(self):
        self.write_eve([alert(1)] + [{"event_type": "flow", "pad": "x" * 200}] * 50 + [alert(2)])

        with mock.patch.object(suricata_telemetry, "open", wraps=open, create=True) as mock_open:
            alerts = suricata_telemetry.get_suricata_alerts(limit=1)

        self.assertEqual([a["src_ip"] for a in alerts], ["10.0.0.2"])
        mock_open.assert_called_once_with(self.eve_path, "rb")

    def test_scan_stops_at_the_byte_limit_and_drops_the_cut_line(self):
        self.write_eve([alert(1), alert(2), alert(3)])
        line_bytes = len(json.dumps(alert(3))) + 1

        read = list(suricata_telemetry.iter_lines_reversed(self.eve_path, max_bytes=line_bytes + 10))

        self.assertEqual([l for l in read if l], [json.dumps(alert(3)).encode()])


if __name__ == "__main__":
    unittest.main()
