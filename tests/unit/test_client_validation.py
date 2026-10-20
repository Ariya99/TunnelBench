"""Unit tests for Phase 6 Iranian-Network Client-Side Validation."""

import socket
import unittest
from unittest.mock import MagicMock, patch

from tunnelbench.models import CheckStatus, ErrorCode
from tunnelbench.validation.client_check import ClientNetworkValidator


class TestClientValidation(unittest.TestCase):

    def test_bogon_dns_injection_detection(self):
        validator = ClientNetworkValidator(target_host="vps.example.com", target_port=443)

        with patch("socket.gethostbyname", return_value="10.10.34.35"):
            probe, ip = validator.probe_dns_resolution()
            self.assertEqual(probe.status, CheckStatus.FAIL)
            self.assertEqual(probe.error_code, ErrorCode.DNS_BOGON_INJECTED)
            self.assertIn("10.10.34.35", probe.error_message)

    def test_normal_dns_resolution(self):
        validator = ClientNetworkValidator(target_host="clean.example.com", target_port=443)

        with patch("socket.gethostbyname", return_value="127.0.0.1"):
            probe, ip = validator.probe_dns_resolution()
            self.assertEqual(probe.status, CheckStatus.FAIL)
            self.assertEqual(probe.error_code, ErrorCode.DNS_BOGON_INJECTED)

    def test_clean_public_dns_resolution(self):
        validator = ClientNetworkValidator(target_host="clean.example.com", target_port=443)

        with patch("socket.gethostbyname", return_value="93.184.216.34"):
            probe, ip = validator.probe_dns_resolution()
            self.assertEqual(probe.status, CheckStatus.PASS)
            self.assertEqual(ip, "93.184.216.34")

    def test_tcp_connect_timeout(self):
        validator = ClientNetworkValidator(target_host="127.0.0.1", target_port=443)

        with patch("socket.socket.connect", side_effect=socket.timeout):
            probe, connected = validator.probe_tcp_connect("127.0.0.1")
            self.assertEqual(probe.status, CheckStatus.FAIL)
            self.assertEqual(probe.error_code, ErrorCode.TCP_TIMEOUT)
            self.assertFalse(connected)

    def test_tcp_connect_reset(self):
        validator = ClientNetworkValidator(target_host="127.0.0.1", target_port=443)

        with patch("socket.socket.connect", side_effect=ConnectionRefusedError):
            probe, connected = validator.probe_tcp_connect("127.0.0.1")
            self.assertEqual(probe.status, CheckStatus.FAIL)
            self.assertEqual(probe.error_code, ErrorCode.TCP_RESET)
            self.assertFalse(connected)

    def test_client_run_all(self):
        validator = ClientNetworkValidator(
            target_host="127.0.0.1",
            target_port=443,
            isp="Irancell",
            connection_type="mobile",
            region="Tehran",
        )

        with patch.object(validator, "probe_dns_resolution") as mock_dns, \
             patch.object(validator, "probe_tcp_connect") as mock_tcp, \
             patch.object(validator, "probe_tls_handshake") as mock_tls:

            from tunnelbench.models import ProbeResult
            mock_dns.return_value = (
                ProbeResult("dns", "DNS", "dns", CheckStatus.PASS, duration_ms=10.0),
                "127.0.0.1",
            )
            mock_tcp.return_value = (
                ProbeResult("tcp", "TCP", "tcp", CheckStatus.PASS, duration_ms=80.0),
                True,
            )
            mock_tls.return_value = ProbeResult("tls", "TLS", "tls", CheckStatus.PASS, duration_ms=120.0)

            report = validator.run_all(repeat=1)
            self.assertEqual(report.status, CheckStatus.PASS)
            self.assertEqual(len(report.results), 3)
            self.assertEqual(report.environment["isp"], "Irancell")


if __name__ == "__main__":
    unittest.main()
