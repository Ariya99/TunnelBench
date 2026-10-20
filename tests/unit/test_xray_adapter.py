"""Unit tests for Xray REALITY Protocol Adapter."""

import unittest
from unittest.mock import MagicMock, patch
from tunnelbench.adapters.xray_reality import XrayRealityAdapter
from tunnelbench.models import CheckStatus, VPSProfile
from tunnelbench.remote.ssh import SSHResult


class TestXrayAdapter(unittest.TestCase):

    def setUp(self):
        self.profile = VPSProfile(
            name="test-vps",
            host="198.51.100.1",
            port=22,
            user="root",
            tags=["unit-test"],
        )

    def test_adapter_metadata(self):
        adapter = XrayRealityAdapter()
        self.assertEqual(adapter.name, "xray-reality")
        self.assertEqual(adapter.status.value, "SUPPORTED")

    def test_build_deployment_plan(self):
        adapter = XrayRealityAdapter()
        plan = adapter.build_deployment_plan(self.profile)

        self.assertEqual(plan.adapter_name, "xray-reality")
        self.assertEqual(plan.exposed_ports, [443])
        self.assertGreaterEqual(len(plan.actions), 5)
        self.assertIn("xray-core", plan.container_image or "")

    def test_require_user_approval_auto(self):
        adapter = XrayRealityAdapter()
        plan = MagicMock()
        self.assertTrue(adapter.require_user_approval(plan, auto_approve=True))

    @patch("builtins.input", return_value="n")
    def test_require_user_approval_reject(self, mock_input):
        adapter = XrayRealityAdapter()
        plan = MagicMock()
        plan.actions = ["action1"]
        plan.exposed_ports = [443]
        plan.container_image = "img"
        plan.config_path = "/path"
        plan.target_vps = "target"
        self.assertFalse(adapter.require_user_approval(plan, auto_approve=False))

    def test_prerequisites_check(self):
        mock_ssh = MagicMock()
        def fake_prereq(cmd: str) -> SSHResult:
            if "docker" in cmd:
                return SSHResult(0, "Docker version 26.1\nOK\n", "", 10.0)
            elif "ss -tlpn" in cmd:
                return SSHResult(0, "", "", 10.0)  # Empty means port 443 is free
            return SSHResult(0, "", "", 10.0)

        mock_ssh.run_command.side_effect = fake_prereq

        adapter = XrayRealityAdapter()
        probes = adapter.check_prerequisites(self.profile, mock_ssh)

        self.assertEqual(len(probes), 2)
        self.assertTrue(all(p.status == CheckStatus.PASS for p in probes))

    def test_deploy_mock(self):
        mock_ssh = MagicMock()

        def fake_run(cmd: str) -> SSHResult:
            if "x25519" in cmd:
                return SSHResult(
                    0,
                    "Private key: FAKE_PRIV_KEY_FOR_TESTS_1234567890123456789=\n"
                    "Public key: FAKE_PUB_KEY_FOR_TESTS_1234567890123456789=\n",
                    "",
                    50.0,
                )
            elif "cat << 'EOF'" in cmd:
                return SSHResult(0, "", "", 30.0)
            elif "docker run -d" in cmd:
                return SSHResult(0, "container_id_12345\n", "", 100.0)
            elif "docker inspect" in cmd:
                return SSHResult(0, "true\n", "", 20.0)
            elif "ss -tlpn" in cmd:
                return SSHResult(0, "LISTEN 0 128 0.0.0.0:443\n", "", 20.0)
            return SSHResult(0, "", "", 10.0)

        mock_ssh.run_command.side_effect = fake_run

        adapter = XrayRealityAdapter()
        plan = adapter.build_deployment_plan(self.profile)

        with patch("time.sleep"):  # Avoid sleep during test
            success, probes, client_data = adapter.deploy(self.profile, plan, mock_ssh)

        self.assertTrue(success)
        self.assertIn("client_link", client_data)
        self.assertIn("vless://", client_data["client_link"])
        self.assertEqual(client_data["adapter"], "xray-reality")


if __name__ == "__main__":
    unittest.main()
