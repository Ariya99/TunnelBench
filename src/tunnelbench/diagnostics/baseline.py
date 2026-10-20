"""Phase 2: Foreign VPS Baseline Diagnostics.

Executes non-destructive, strictly read-only diagnostics across the foreign VPS
to verify connectivity, system resources, and outbound internet transit.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional

from tunnelbench.models import CheckStatus, ErrorCode, ProbeResult, ReportModel, TestPhase, VPSProfile
from tunnelbench.remote.ssh import SSHClient, SSHResult


class BaselineDiagnostics:
    """Orchestrates foreign VPS baseline health and capability checks."""

    def __init__(self, profile: VPSProfile, ssh_client: Optional[SSHClient] = None) -> None:
        self.profile = profile
        self.ssh = ssh_client or SSHClient(profile)

    def check_ssh_connectivity(self) -> Tuple[ProbeResult, bool]:
        """Probes basic SSH authentication and host key validity."""
        start = time.perf_counter()
        res = self.ssh.run_command("echo '__TUNNELBENCH_SSH_OK__'")
        duration = (time.perf_counter() - start) * 1000

        if res.success and "__TUNNELBENCH_SSH_OK__" in res.stdout:
            return (
                ProbeResult(
                    probe_id="baseline_ssh_reachability",
                    name="SSH Host Key & Authentication",
                    category="system",
                    status=CheckStatus.PASS,
                    target=f"{self.profile.host}:{self.profile.port}",
                    duration_ms=duration,
                    details={"latency_ms": round(res.duration_ms, 2)},
                ),
                True,
            )

        return (
            ProbeResult(
                probe_id="baseline_ssh_reachability",
                name="SSH Host Key & Authentication",
                category="system",
                status=CheckStatus.FAIL,
                target=f"{self.profile.host}:{self.profile.port}",
                duration_ms=duration,
                error_code=res.error_code,
                error_message=res.error_message or res.stderr.strip(),
            ),
            False,
        )

    def check_os_info(self) -> ProbeResult:
        """Inspects remote architecture and distribution."""
        cmd = "uname -m && uname -r && cat /etc/os-release"
        res = self.ssh.run_command(cmd)
        if not res.success:
            return ProbeResult(
                probe_id="baseline_os_info",
                name="Remote OS & Architecture",
                category="system",
                status=CheckStatus.FAIL,
                duration_ms=res.duration_ms,
                error_code=res.error_code,
                error_message=res.error_message,
            )

        lines = res.stdout.strip().splitlines()
        arch = lines[0] if lines else "unknown"
        kernel = lines[1] if len(lines) > 1 else "unknown"
        os_id = "linux"
        for line in lines[2:]:
            if line.startswith("PRETTY_NAME="):
                os_id = line.split("=", 1)[1].strip('"\'')
                break

        return ProbeResult(
            probe_id="baseline_os_info",
            name="Remote OS & Architecture",
            category="system",
            status=CheckStatus.PASS,
            duration_ms=res.duration_ms,
            details={"architecture": arch, "kernel": kernel, "os": os_id},
        )

    def check_system_resources(self) -> ProbeResult:
        """Checks available CPU cores, RAM, and root disk capacity."""
        cmd = "nproc && grep MemTotal /proc/meminfo && grep MemAvailable /proc/meminfo && df -k /"
        res = self.ssh.run_command(cmd)
        if not res.success:
            return ProbeResult(
                probe_id="baseline_resources",
                name="Hardware Resources & Capacity",
                category="system",
                status=CheckStatus.FAIL,
                duration_ms=res.duration_ms,
                error_code=res.error_code,
                error_message=res.error_message,
            )

        lines = res.stdout.strip().splitlines()
        cores = int(lines[0]) if lines and lines[0].isdigit() else 1
        mem_avail_mb = 0
        mem_total_mb = 0
        disk_avail_gb = 0.0

        for line in lines:
            if "MemTotal:" in line:
                m = re.search(r"(\d+)", line)
                if m:
                    mem_total_mb = int(m.group(1)) // 1024
            elif "MemAvailable:" in line:
                m = re.search(r"(\d+)", line)
                if m:
                    mem_avail_mb = int(m.group(1)) // 1024

        # Parse df -k /
        df_lines = [l for l in lines if "/" in l and "Filesystem" not in l]
        if df_lines:
            parts = df_lines[-1].split()
            if len(parts) >= 4 and parts[3].isdigit():
                disk_avail_gb = round(int(parts[3]) / (1024 * 1024), 2)

        # Evaluate minimum suitability
        status = CheckStatus.PASS
        warning = ""
        if mem_avail_mb < 256:
            status = CheckStatus.INCONCLUSIVE
            warning = "Available memory is low (< 256MB). Heavy container loads may OOM."
        elif disk_avail_gb < 1.0:
            status = CheckStatus.INCONCLUSIVE
            warning = "Available disk is low (< 1GB)."

        return ProbeResult(
            probe_id="baseline_resources",
            name="Hardware Resources & Capacity",
            category="system",
            status=status,
            duration_ms=res.duration_ms,
            details={
                "cpu_cores": cores,
                "mem_total_mb": mem_total_mb,
                "mem_available_mb": mem_avail_mb,
                "disk_available_gb": disk_avail_gb,
            },
            error_message=warning,
        )

    def check_outbound_internet(self) -> ProbeResult:
        """Verifies the VPS has healthy outbound DNS and HTTPS connectivity."""
        cmd = "getent hosts cloudflare.com > /dev/null && curl -s -m 5 -o /dev/null -w '%{http_code}' https://1.1.1.1"
        res = self.ssh.run_command(cmd)
        if res.success and ("200" in res.stdout or "301" in res.stdout or "302" in res.stdout):
            return ProbeResult(
                probe_id="baseline_vps_egress",
                name="VPS Outbound Transit (DNS & HTTPS)",
                category="http",
                status=CheckStatus.PASS,
                duration_ms=res.duration_ms,
                details={"http_code": res.stdout.strip()},
            )

        return ProbeResult(
            probe_id="baseline_vps_egress",
            name="VPS Outbound Transit (DNS & HTTPS)",
            category="http",
            status=CheckStatus.FAIL,
            duration_ms=res.duration_ms,
            error_code=ErrorCode.UNKNOWN_ERROR,
            error_message="VPS could not resolve or reach external HTTPS test endpoints.",
        )

    def check_docker_runtime(self) -> ProbeResult:
        """Verifies if Docker is installed and active on the remote VPS."""
        cmd = "docker --version && docker ps > /dev/null 2>&1 && echo 'DOCKER_ACTIVE'"
        res = self.ssh.run_command(cmd)
        if res.success and "DOCKER_ACTIVE" in res.stdout:
            version_str = res.stdout.splitlines()[0]
            return ProbeResult(
                probe_id="baseline_docker_status",
                name="Remote Docker Runtime",
                category="system",
                status=CheckStatus.PASS,
                duration_ms=res.duration_ms,
                details={"docker_version": version_str},
            )

        return ProbeResult(
            probe_id="baseline_docker_status",
            name="Remote Docker Runtime",
            category="system",
            status=CheckStatus.INCONCLUSIVE,
            duration_ms=res.duration_ms,
            details={"optional": True},
            error_message="Docker is not active or accessible without sudo. Required for containerized adapters.",
        )

    def run_all(self) -> ReportModel:
        """Runs complete baseline diagnostics against the foreign VPS."""
        start_time = time.perf_counter()
        results: List[ProbeResult] = []

        ssh_probe, connected = self.check_ssh_connectivity()
        results.append(ssh_probe)

        if not connected:
            # If SSH fails, remaining remote checks cannot run
            duration_sec = time.perf_counter() - start_time
            report = ReportModel(
                test_phase=TestPhase.BASELINE,
                status=CheckStatus.FAIL,
                vps_profile=self.profile.to_dict(),
                results=results,
            )
            report.compute_summary(duration_sec)
            return report

        # Run remaining read-only probes
        results.append(self.check_os_info())
        results.append(self.check_system_resources())
        results.append(self.check_outbound_internet())
        results.append(self.check_docker_runtime())

        duration_sec = time.perf_counter() - start_time
        report = ReportModel(
            test_phase=TestPhase.BASELINE,
            status=CheckStatus.PASS,
            vps_profile=self.profile.to_dict(),
            results=results,
        )
        report.compute_summary(duration_sec)
        return report
