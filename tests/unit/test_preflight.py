"""Unit tests for Phase 0 Preflight Doctor."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tunnelbench.diagnostics.preflight import PreflightChecker
from tunnelbench.models import CheckStatus


class TestPreflight(unittest.TestCase):

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.report_dir = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def test_preflight_all(self):
        checker = PreflightChecker(report_dir=self.report_dir)
        report = checker.run_all()

        self.assertGreaterEqual(report.summary.total_checks, 5)

        # Python check must pass in our Python 3.12 environment
        py_check = next(r for r in report.results if r.probe_id == "preflight_python_version")
        self.assertEqual(py_check.status, CheckStatus.PASS)

        # Storage check must pass
        storage_check = next(r for r in report.results if r.probe_id == "preflight_report_storage")
        self.assertEqual(storage_check.status, CheckStatus.PASS)

    @patch("shutil.which")
    def test_preflight_missing_ssh(self, mock_which):
        mock_which.return_value = None
        checker = PreflightChecker(report_dir=self.report_dir)
        res = checker.check_ssh_client()
        self.assertEqual(res.status, CheckStatus.FAIL)
        self.assertIn("not found", res.error_message)


if __name__ == "__main__":
    unittest.main()
