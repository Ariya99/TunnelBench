"""Unit tests for SSH client security constraints and command construction."""

import subprocess
import unittest
from unittest.mock import MagicMock, patch

from tunnelbench.models import ErrorCode, VPSProfile
from tunnelbench.remote.ssh import SSHClient


class TestSSHSecurity(unittest.TestCase):

    def setUp(self):
        self.profile = VPSProfile(
            name="test-vps",
            host="198.51.100.1",
            port=22,
            user="root",
            auth_method="key",
            tags=["unit-test"],
        )

    def test_ssh_command_construction(self):
        client = SSHClient(self.profile)
        base_cmd = client._build_ssh_base_command()

        # Enforce strict host key verification
        self.assertIn("-o", base_cmd)
        self.assertIn("StrictHostKeyChecking=yes", base_cmd)
        self.assertIn("BatchMode=yes", base_cmd)
        self.assertIn("-p", base_cmd)
        self.assertIn("22", base_cmd)
        self.assertIn("root@198.51.100.1", base_cmd)

    @patch("subprocess.run")
    def test_ssh_host_key_mismatch_detection(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["ssh"],
            returncode=255,
            stdout="",
            stderr="@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n"
                   "@    WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!     @\n"
                   "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n"
                   "Host key verification failed.\n",
        )
        client = SSHClient(self.profile)
        res = client.run_command("uname -a")

        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ErrorCode.SSH_HOST_KEY_MISMATCH)
        self.assertIn("Host key verification failed", res.error_message)

    @patch("subprocess.run")
    def test_ssh_auth_failure_detection(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["ssh"],
            returncode=255,
            stdout="",
            stderr="Permission denied (publickey).\n",
        )
        client = SSHClient(self.profile)
        res = client.run_command("uname -a")

        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ErrorCode.SSH_AUTH_FAILED)

    @patch("subprocess.run")
    def test_ssh_timeout_handling(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["ssh"], timeout=10)
        client = SSHClient(self.profile, timeout_seconds=10)
        res = client.run_command("sleep 20")

        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ErrorCode.SSH_TIMEOUT)
        self.assertIn("exceeded 10s timeout", res.error_message)


if __name__ == "__main__":
    unittest.main()
