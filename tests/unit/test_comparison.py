"""Unit tests for Run Comparator and Metric Drift Engine."""

import unittest
from tunnelbench.comparison.comparator import ReportComparator


class TestComparison(unittest.TestCase):

    def test_comparator_detects_deltas(self):
        report_a = {
            "run_id": "run-a-1111",
            "test_phase": "client_check",
            "status": "PASS",
            "environment": {"isp": "MCI", "connection_type": "mobile"},
            "summary": {"passed": 2, "failed": 0, "duration_seconds": 1.0},
            "results": [
                {"probe_id": "tcp", "name": "TCP", "status": "PASS", "duration_ms": 100.0, "error_code": "NONE"},
                {"probe_id": "tls", "name": "TLS", "status": "PASS", "duration_ms": 150.0, "error_code": "NONE"},
            ],
        }

        report_b = {
            "run_id": "run-b-2222",
            "test_phase": "client_check",
            "status": "FAIL",
            "environment": {"isp": "MCI", "connection_type": "mobile"},
            "summary": {"passed": 1, "failed": 1, "duration_seconds": 1.5},
            "results": [
                {"probe_id": "tcp", "name": "TCP", "status": "PASS", "duration_ms": 120.0, "error_code": "NONE"},
                {"probe_id": "tls", "name": "TLS", "status": "FAIL", "duration_ms": 300.0, "error_code": "TLS_SNI_BLOCKED"},
            ],
        }

        diff = ReportComparator.compare(report_a, report_b)
        self.assertTrue(diff["equivalent_conditions"])
        self.assertEqual(diff["status_transition"], "PASS -> FAIL")
        self.assertEqual(diff["passed_delta"], -1)
        self.assertEqual(diff["failed_delta"], 1)

        tls_delta = next(p for p in diff["probe_deltas"] if p["probe_id"] == "tls")
        self.assertTrue(tls_delta["status_changed"])
        self.assertEqual(tls_delta["status_a"], "PASS")
        self.assertEqual(tls_delta["status_b"], "FAIL")
        self.assertEqual(tls_delta["latency_delta_ms"], 150.0)

        summary_text = ReportComparator.format_text_summary(diff)
        self.assertIn("PASS -> FAIL", summary_text)
        self.assertIn("tls", summary_text)


if __name__ == "__main__":
    unittest.main()
