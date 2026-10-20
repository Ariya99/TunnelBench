"""Phase 6: Iranian-Network Client-Side Diagnostic Engine.

Executes sequential, safe measurement probes from the operator's current access network,
recording DNS tampering, TCP reachability, TLS handshake status, and tunnel forwarding.
"""

from __future__ import annotations

import ipaddress
import platform
import socket
import ssl
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import urllib.request
import urllib.error

from tunnelbench.models import CheckStatus, ErrorCode, ProbeResult, ReportModel, TestPhase, VPSProfile


# Subnets heavily associated with Iranian DNS redirection and block injection
KNOWN_BOGON_NETWORKS = [
    ipaddress.ip_network("10.10.34.0/24"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("0.0.0.0/8"),
]


class ClientNetworkValidator:
    """Probes client-to-VPS reachability and characterizes filtering failure modes."""

    def __init__(
        self,
        target_host: str,
        target_port: int = 443,
        sni: str = "www.microsoft.com",
        proxy_url: Optional[str] = None,
        isp: str = "unspecified",
        connection_type: str = "unknown",
        region: str = "unspecified",
        timeout: float = 6.0,
    ) -> None:
        self.target_host = target_host
        self.target_port = target_port
        self.sni = sni
        self.proxy_url = proxy_url
        self.isp = isp
        self.connection_type = connection_type
        self.region = region
        self.timeout = timeout

    def probe_dns_resolution(self) -> Tuple[ProbeResult, Optional[str]]:
        """Resolves target host and checks for known Iranian bogon IP poisoning."""
        start = time.perf_counter()

        # If target is already an IP, DNS lookup is not needed
        try:
            ipaddress.ip_address(self.target_host)
            duration = (time.perf_counter() - start) * 1000
            return (
                ProbeResult(
                    probe_id="client_dns_resolution",
                    name="DNS Resolution & Bogon Check",
                    category="dns",
                    status=CheckStatus.PASS,
                    target=self.target_host,
                    duration_ms=duration,
                    details={"resolved_ip": self.target_host, "is_literal_ip": True},
                ),
                self.target_host,
            )
        except ValueError:
            pass

        try:
            resolved_ip = socket.gethostbyname(self.target_host)
            duration = (time.perf_counter() - start) * 1000
            ip_obj = ipaddress.ip_address(resolved_ip)

            # Check if resolved IP falls into known Iranian bogon ranges
            for bogon_net in KNOWN_BOGON_NETWORKS:
                if ip_obj in bogon_net:
                    return (
                        ProbeResult(
                            probe_id="client_dns_resolution",
                            name="DNS Resolution & Bogon Check",
                            category="dns",
                            status=CheckStatus.FAIL,
                            target=self.target_host,
                            duration_ms=duration,
                            details={"resolved_ip": resolved_ip, "bogon_match": str(bogon_net)},
                            error_code=ErrorCode.DNS_BOGON_INJECTED,
                            error_message=(
                                f"DNS tampering detected: Host '{self.target_host}' resolved to "
                                f"censorship bogon address {resolved_ip} in {bogon_net}"
                            ),
                        ),
                        resolved_ip,
                    )

            return (
                ProbeResult(
                    probe_id="client_dns_resolution",
                    name="DNS Resolution & Bogon Check",
                    category="dns",
                    status=CheckStatus.PASS,
                    target=self.target_host,
                    duration_ms=duration,
                    details={"resolved_ip": resolved_ip},
                ),
                resolved_ip,
            )

        except socket.gaierror as e:
            duration = (time.perf_counter() - start) * 1000
            return (
                ProbeResult(
                    probe_id="client_dns_resolution",
                    name="DNS Resolution & Bogon Check",
                    category="dns",
                    status=CheckStatus.FAIL,
                    target=self.target_host,
                    duration_ms=duration,
                    error_code=ErrorCode.DNS_NXDOMAIN,
                    error_message=f"DNS resolution failed: {e}",
                ),
                None,
            )
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return (
                ProbeResult(
                    probe_id="client_dns_resolution",
                    name="DNS Resolution & Bogon Check",
                    category="dns",
                    status=CheckStatus.FAIL,
                    target=self.target_host,
                    duration_ms=duration,
                    error_code=ErrorCode.DNS_TIMEOUT,
                    error_message=f"DNS query timed out or failed: {e}",
                ),
                None,
            )

    def probe_tcp_connect(self, ip_to_connect: str) -> Tuple[ProbeResult, bool]:
        """Probes TCP 3-way handshake to destination IP and port."""
        start = time.perf_counter()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)

        try:
            sock.connect((ip_to_connect, self.target_port))
            duration = (time.perf_counter() - start) * 1000
            return (
                ProbeResult(
                    probe_id="client_tcp_connect",
                    name="TCP 3-Way Handshake",
                    category="tcp",
                    status=CheckStatus.PASS,
                    target=f"{ip_to_connect}:{self.target_port}",
                    duration_ms=duration,
                    details={"rtt_ms": round(duration, 2)},
                ),
                True,
            )
        except socket.timeout:
            duration = (time.perf_counter() - start) * 1000
            return (
                ProbeResult(
                    probe_id="client_tcp_connect",
                    name="TCP 3-Way Handshake",
                    category="tcp",
                    status=CheckStatus.FAIL,
                    target=f"{ip_to_connect}:{self.target_port}",
                    duration_ms=duration,
                    error_code=ErrorCode.TCP_TIMEOUT,
                    error_message=f"TCP connection to {ip_to_connect}:{self.target_port} timed out after {self.timeout}s (SYN packet dropped).",
                ),
                False,
            )
        except ConnectionRefusedError:
            duration = (time.perf_counter() - start) * 1000
            return (
                ProbeResult(
                    probe_id="client_tcp_connect",
                    name="TCP 3-Way Handshake",
                    category="tcp",
                    status=CheckStatus.FAIL,
                    target=f"{ip_to_connect}:{self.target_port}",
                    duration_ms=duration,
                    error_code=ErrorCode.TCP_RESET,
                    error_message=(
                        f"TCP connection reset/refused. "
                        f"Port may be closed on VPS or reset by DPI."
                    ),
                ),
                False,
            )
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return (
                ProbeResult(
                    probe_id="client_tcp_connect",
                    name="TCP 3-Way Handshake",
                    category="tcp",
                    status=CheckStatus.FAIL,
                    target=f"{ip_to_connect}:{self.target_port}",
                    duration_ms=duration,
                    error_code=ErrorCode.UNKNOWN_ERROR,
                    error_message=f"TCP connection failed: {e}",
                ),
                False,
            )
        finally:
            try:
                sock.close()
            except Exception:
                pass

    def probe_tls_handshake(self, ip_to_connect: str) -> ProbeResult:
        """Tests TLS ClientHello negotiation with decoy SNI."""
        start = time.perf_counter()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)

        # Context configured not to enforce cert check since REALITY re-encrypts or proxies
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        try:
            sock.connect((ip_to_connect, self.target_port))
            tls_sock = ctx.wrap_socket(sock, server_hostname=self.sni)
            cipher = tls_sock.cipher()
            version = tls_sock.version()
            duration = (time.perf_counter() - start) * 1000
            tls_sock.close()
            return ProbeResult(
                probe_id="client_tls_handshake",
                name="TLS Handshake with Decoy SNI",
                category="tls",
                status=CheckStatus.PASS,
                target=f"{self.sni} via {ip_to_connect}:{self.target_port}",
                duration_ms=duration,
                details={
                    "cipher": cipher[0] if cipher else "unknown",
                    "tls_version": version,
                    "sni": self.sni,
                },
            )
        except socket.timeout:
            duration = (time.perf_counter() - start) * 1000
            return ProbeResult(
                probe_id="client_tls_handshake",
                name="TLS Handshake with Decoy SNI",
                category="tls",
                status=CheckStatus.FAIL,
                target=f"{self.sni} via {ip_to_connect}:{self.target_port}",
                duration_ms=duration,
                error_code=ErrorCode.TLS_TIMEOUT,
                error_message=f"TLS handshake timed out. Decoy SNI '{self.sni}' or TLS fingerprint may be blocked.",
            )
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            err_str = str(e).lower()
            code = ErrorCode.TLS_SNI_BLOCKED if "reset" in err_str or "closed" in err_str else ErrorCode.UNKNOWN_ERROR
            return ProbeResult(
                probe_id="client_tls_handshake",
                name="TLS Handshake with Decoy SNI",
                category="tls",
                status=CheckStatus.FAIL,
                target=f"{self.sni} via {ip_to_connect}:{self.target_port}",
                duration_ms=duration,
                error_code=code,
                error_message=f"TLS negotiation failed: {e}",
            )
        finally:
            try:
                sock.close()
            except Exception:
                pass

    def probe_tunnel_http(self) -> ProbeResult:
        """Verifies HTTP/HTTPS forwarding through configured local proxy."""
        if not self.proxy_url:
            return ProbeResult(
                probe_id="client_tunnel_forwarding",
                name="In-Tunnel HTTP Forwarding",
                category="http",
                status=CheckStatus.NOT_RUN,
                error_message="No local proxy URL provided (e.g., socks5://127.0.0.1:10808 or http://127.0.0.1:10809).",
            )

        start = time.perf_counter()
        test_url = "http://cp.cloudflare.com/generate_204"

        try:
            handler = urllib.request.ProxyHandler({"http": self.proxy_url, "https": self.proxy_url})
            opener = urllib.request.build_opener(handler)
            req = urllib.request.Request(test_url, headers={"User-Agent": "TunnelBench/0.1.0"})
            with opener.open(req, timeout=self.timeout) as response:
                status_code = response.getcode()
                duration = (time.perf_counter() - start) * 1000
                if status_code in (200, 204):
                    return ProbeResult(
                        probe_id="client_tunnel_forwarding",
                        name="In-Tunnel HTTP Forwarding",
                        category="http",
                        status=CheckStatus.PASS,
                        target=test_url,
                        duration_ms=duration,
                        details={"http_code": status_code, "proxy": self.proxy_url},
                    )
                return ProbeResult(
                    probe_id="client_tunnel_forwarding",
                    name="In-Tunnel HTTP Forwarding",
                    category="http",
                    status=CheckStatus.INCONCLUSIVE,
                    target=test_url,
                    duration_ms=duration,
                    details={"http_code": status_code},
                    error_message=f"Received unexpected status {status_code}",
                )
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return ProbeResult(
                probe_id="client_tunnel_forwarding",
                name="In-Tunnel HTTP Forwarding",
                category="http",
                status=CheckStatus.FAIL,
                target=test_url,
                duration_ms=duration,
                error_code=ErrorCode.UNKNOWN_ERROR,
                error_message=f"In-tunnel request failed through {self.proxy_url}: {e}",
            )

    def run_all(self, repeat: int = 1) -> ReportModel:
        """Runs the Iranian client-side diagnostic sequence."""
        start_time = time.perf_counter()
        results: List[ProbeResult] = []

        # 1. DNS Resolution
        dns_probe, resolved_ip = self.probe_dns_resolution()
        results.append(dns_probe)

        target_ip = resolved_ip or self.target_host

        # 2. TCP Handshake (run repeat times for latency measurement)
        tcp_probes: List[ProbeResult] = []
        for _ in range(max(1, repeat)):
            tcp_probe, tcp_connected = self.probe_tcp_connect(target_ip)
            tcp_probes.append(tcp_probe)

        # Average TCP results if repeated
        results.extend(tcp_probes)
        any_tcp_connected = any(p.status == CheckStatus.PASS for p in tcp_probes)

        # 3. TLS Handshake (only if TCP connected)
        if any_tcp_connected:
            tls_probe = self.probe_tls_handshake(target_ip)
            results.append(tls_probe)

        # 4. In-Tunnel Forwarding (if proxy configured)
        if self.proxy_url:
            forwarding_probe = self.probe_tunnel_http()
            results.append(forwarding_probe)

        duration_sec = time.perf_counter() - start_time
        report = ReportModel(
            test_phase=TestPhase.CLIENT_CHECK,
            status=CheckStatus.PASS,
            environment={
                "client_os": platform.system(),
                "client_python": sys.version.split()[0],
                "isp": self.isp,
                "connection_type": self.connection_type,
                "region": self.region,
            },
            results=results,
        )
        report.compute_summary(duration_sec)
        return report
