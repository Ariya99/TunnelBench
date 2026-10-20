"""Unit tests for Reporting Engine and JSON/CSV Exporters."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from tunnelbench.models import CheckStatus, ProbeResult, ReportModel, TestPhase
from tunnelbench.reporting.export import ReportManager


class TestReporting(unittest.TestCase):

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.report_dir = Path(self.td.name)
        self.rep_mgr = ReportManager(report_dir=self.report_dir)

    def tearDown(self):
        self.td.cleanup()

    def test_save_and_load_report(self):
        probe = ProbeResult(
            probe_id="p1",
            name="Probe 1",
            category="tcp",
            status=CheckStatus.PASS,
            target="198.51.100.1:443",
            duration_ms=45.2,
        )
        report = ReportModel(
            test_phase=TestPhase.CLIENT_CHECK,
            status=CheckStatus.PASS,
            environment={"isp": "Irancell", "connection_type": "mobile"},
            results=[probe],
        )
        report.compute_summary(1.5)

        jpath, cpath = self.rep_mgr.save_report(report)
        self.assertTrue(jpath.exists())
        self.assertTrue(cpath.exists())

        loaded = self.rep_mgr.load_report(report.run_id)
        self.assertEqual(loaded["run_id"], report.run_id)
        self.assertEqual(loaded["test_phase"], "client_check")
        self.assertEqual(loaded["status"], "PASS")

        with open(cpath, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            self.assertEqual(len(reader), 1)
            self.assertEqual(reader[0]["probe_id"], "p1")
            self.assertEqual(reader[0]["isp"], "Irancell")
            self.assertEqual(reader[0]["probe_status"], "PASS")

    def test_report_redaction_on_save(self):
        probe = ProbeResult(
            probe_id="p_secret",
            name="Probe Secret",
            category="http",
            status=CheckStatus.PASS,
            details={"token": "Bearer ya29.secretToken1234567890"},
            error_message="Key was AIzaSySecretApiKey123456789012345678",
        )
        report = ReportModel(
            test_phase=TestPhase.TARGET_CHECK,
            status=CheckStatus.PASS,
            results=[probe],
        )
        report.compute_summary(0.5)

        jpath, cpath = self.rep_mgr.save_report(report)
        with open(jpath, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertNotIn("AIzaSy", content)
            self.assertIn("[REDACTED_API_KEY]", content)
            self.assertIn("Bearer [REDACTED_TOKEN]", content)


if __name__ == "__main__":
    unittest.main()
