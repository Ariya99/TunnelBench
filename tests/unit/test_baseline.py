"""Unit tests for Phase 2 Foreign VPS Baseline Diagnostics."""

import unittest
from unittest.mock import MagicMock
from tunnelbench.diagnostics.baseline import BaselineDiagnostics
from tunnelbench.models import CheckStatus, VPSProfile
from tunnelbench.remote.ssh import SSHResult


class TestBaseline(unittest.TestCase):

    def setUp(self):
        self.profile = VPSProfile(
            name="test-vps",
            host="198.51.100.1",
            port=22,
            user="root",
            tags=["unit-test"],
        )

    def test_baseline_successful_run(self):
        mock_ssh = MagicMock()

        def fake_run(cmd: str) -> SSHResult:
            if "__TUNNELBENCH_SSH_OK__" in cmd:
                return SSHResult(0, "__TUNNELBENCH_SSH_OK__\n", "", 50.0)
            elif "cat /etc/os-release" in cmd:
                return SSHResult(
                    0,
                    "x86_64\n6.8.0-45-generic\nPRETTY_NAME=\"Ubuntu 24.04 LTS\"\nNAME=\"Ubuntu\"\n",
                    "",
                    30.0,
                )
            elif "/proc/meminfo" in cmd:
                return SSHResult(
                    0,
                    "4\nMemTotal:        4024828 kB\nMemAvailable:    3124500 kB\n/dev/sda1 40960000 10240000 30720000 25% /\n",
                    "",
                    25.0,
                )
            elif "getent hosts cloudflare.com" in cmd:
                return SSHResult(0, "200\n", "", 40.0)
            elif "docker --version" in cmd:
                return SSHResult(0, "Docker version 26.1.0\nDOCKER_ACTIVE\n", "", 20.0)
            return SSHResult(0, "", "", 10.0)

        mock_ssh.run_command.side_effect = fake_run

        runner = BaselineDiagnostics(self.profile, ssh_client=mock_ssh)
        report = runner.run_all()

        self.assertEqual(report.status, CheckStatus.PASS)
        self.assertGreaterEqual(report.summary.passed, 4)

        os_probe = next(r for r in report.results if r.probe_id == "baseline_os_info")
        self.assertEqual(os_probe.details["architecture"], "x86_64")
        self.assertIn("Ubuntu 24.04", os_probe.details["os"])

        res_probe = next(r for r in report.results if r.probe_id == "baseline_resources")
        self.assertEqual(res_probe.details["cpu_cores"], 4)
        self.assertGreater(res_probe.details["mem_available_mb"], 2000)

    def test_baseline_ssh_disconnect(self):
        mock_ssh = MagicMock()
        mock_ssh.run_command.return_value = SSHResult(-1, "", "Connection refused", 10.0)

        runner = BaselineDiagnostics(self.profile, ssh_client=mock_ssh)
        report = runner.run_all()

        self.assertEqual(report.status, CheckStatus.FAIL)
        self.assertEqual(len(report.results), 1)
        self.assertEqual(report.results[0].status, CheckStatus.FAIL)


if __name__ == "__main__":
    unittest.main()
