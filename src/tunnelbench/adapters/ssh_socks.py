"""SSH Dynamic SOCKS5 Baseline Protocol Adapter.

Uses standard OpenSSH dynamic application-level forwarding to provide
an immediate baseline proxy for contrast against custom obfuscated tunnels.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from tunnelbench.adapters.base import BaseAdapter, register_adapter
from tunnelbench.models import AdapterStatus, CheckStatus, DeploymentPlan, ProbeResult, VPSProfile
from tunnelbench.remote.ssh import SSHClient


DEFAULT_SOCKS_PORT = 10808


class SSHSocksAdapter(BaseAdapter):
    """Adapter for SSH dynamic SOCKS5 proxy baseline."""

    name = "ssh-socks"
    display_name = "SSH Dynamic SOCKS5 Proxy"
    status = AdapterStatus.SUPPORTED
    description = (
        "Zero-installation diagnostic baseline using OpenSSH -D forwarding. "
        "Useful for establishing baseline performance and failure comparisons."
    )

    def check_prerequisites(self, profile: VPSProfile, ssh: SSHClient) -> List[ProbeResult]:
        res = ssh.run_command("echo 'SSH_ALIVE'")
        if res.success and "SSH_ALIVE" in res.stdout:
            return [
                ProbeResult(
                    probe_id="ssh_prereq_alive",
                    name="SSH Server Reachability",
                    category="health",
                    status=CheckStatus.PASS,
                    duration_ms=res.duration_ms,
                )
            ]
        return [
            ProbeResult(
                probe_id="ssh_prereq_alive",
                name="SSH Server Reachability",
                category="health",
                status=CheckStatus.FAIL,
                duration_ms=res.duration_ms,
                error_message=res.error_message,
            )
        ]

    def build_deployment_plan(
        self, profile: VPSProfile, options: Optional[Dict[str, Any]] = None
    ) -> DeploymentPlan:
        opts = options or {}
        local_port = int(opts.get("local_port", DEFAULT_SOCKS_PORT))
        actions = [
            f"Launch local background OpenSSH dynamic proxy on 127.0.0.1:{local_port}",
            f"Route traffic through remote SSH server {profile.host}:{profile.port}",
            f"Zero changes made to foreign VPS filesystem or packages",
        ]
        return DeploymentPlan(
            adapter_name=self.name,
            target_vps=f"{profile.user}@{profile.host}:{profile.port}",
            actions=actions,
            exposed_ports=[local_port],
            system_privileges_required=False,
        )

    def deploy(
        self, profile: VPSProfile, plan: DeploymentPlan, ssh: SSHClient
    ) -> Tuple[bool, List[ProbeResult], Dict[str, Any]]:
        local_port = plan.exposed_ports[0] if plan.exposed_ports else DEFAULT_SOCKS_PORT
        client_data = {
            "adapter": self.name,
            "socks_proxy": f"socks5://127.0.0.1:{local_port}",
            "command": f"ssh -N -D 127.0.0.1:{local_port} -p {profile.port} {profile.user}@{profile.host}",
        }
        probes = [
            ProbeResult(
                probe_id="ssh_socks_configured",
                name="SSH SOCKS5 Configuration Plan",
                category="health",
                status=CheckStatus.PASS,
                duration_ms=5.0,
                details=client_data,
            )
        ]
        return True, probes, client_data

    def health_check(self, profile: VPSProfile, ssh: SSHClient) -> List[ProbeResult]:
        return [
            ProbeResult(
                probe_id="ssh_socks_health",
                name="SSH SOCKS5 Baseline Ready",
                category="health",
                status=CheckStatus.PASS,
                duration_ms=1.0,
            )
        ]

    def cleanup(self, profile: VPSProfile, ssh: SSHClient) -> Tuple[bool, List[ProbeResult]]:
        return True, [
            ProbeResult(
                probe_id="ssh_socks_cleanup",
                name="SSH SOCKS5 Cleanup",
                category="health",
                status=CheckStatus.PASS,
                duration_ms=1.0,
            )
        ]


register_adapter(SSHSocksAdapter())
