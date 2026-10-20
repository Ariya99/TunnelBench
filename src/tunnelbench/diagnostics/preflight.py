"""Phase 0: Environment Preflight Doctor.

Verifies local controller prerequisites, operating system environment,
SSH client availability, optional Docker tooling, and report directory permissions.
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
import time
from pathlib import Path
from typing import List, Tuple

from tunnelbench.models import CheckStatus, ErrorCode, ProbeResult, ReportModel, TestPhase


class PreflightChecker:
    """Executes local environment validation probes."""

    def __init__(self, report_dir: Path | None = None) -> None:
        if report_dir is None:
            env_dir = os.environ.get("TUNNELBENCH_REPORT_DIR")
            if env_dir:
                self.report_dir = Path(env_dir)
            else:
                preferred = Path(os.path.expanduser("~/.local/share/tunnelbench/reports"))
                try:
                    preferred.mkdir(parents=True, exist_ok=True, mode=0o700)
                    self.report_dir = preferred
                except OSError:
                    self.report_dir = Path.cwd() / ".tunnelbench" / "reports"
        else:
            self.report_dir = Path(report_dir)

    def check_python_version(self) -> ProbeResult:
        """Verifies Python is >= 3.11."""
        start = time.perf_counter()
        version = sys.version_info
        duration = (time.perf_counter() - start) * 1000
        details = {
            "version": f"{version.major}.{version.minor}.{version.micro}",
            "executable": sys.executable,
        }
        if version >= (3, 11):
            return ProbeResult(
                probe_id="preflight_python_version",
                name="Python Runtime Version",
                category="system",
                status=CheckStatus.PASS,
                duration_ms=duration,
                details=details,
            )
        return ProbeResult(
            probe_id="preflight_python_version",
            name="Python Runtime Version",
            category="system",
            status=CheckStatus.FAIL,
            duration_ms=duration,
            details=details,
            error_code=ErrorCode.UNKNOWN_ERROR,
            error_message=f"Python >= 3.11 is required. Found {version.major}.{version.minor}",
        )

    def check_os_environment(self) -> ProbeResult:
        """Inspects host platform and architecture."""
        start = time.perf_counter()
        os_name = platform.system()
        arch = platform.machine()
        duration = (time.perf_counter() - start) * 1000
        return ProbeResult(
            probe_id="preflight_os_environment",
            name="Host Operating System",
            category="system",
            status=CheckStatus.PASS,
            duration_ms=duration,
            details={"system": os_name, "release": platform.release(), "machine": arch},
        )

    def check_ssh_client(self) -> ProbeResult:
        """Verifies OpenSSH binary exists on PATH."""
        start = time.perf_counter()
        ssh_path = shutil.which("ssh")
        duration = (time.perf_counter() - start) * 1000
        if ssh_path:
            return ProbeResult(
                probe_id="preflight_ssh_client",
                name="OpenSSH Client Binary",
                category="system",
                status=CheckStatus.PASS,
                duration_ms=duration,
                details={"path": ssh_path},
            )
        return ProbeResult(
            probe_id="preflight_ssh_client",
            name="OpenSSH Client Binary",
            category="system",
            status=CheckStatus.FAIL,
            duration_ms=duration,
            error_code=ErrorCode.UNKNOWN_ERROR,
            error_message="OpenSSH client binary ('ssh') was not found in PATH.",
        )

    def check_docker_client(self) -> ProbeResult:
        """Checks for Docker availability (optional for basic diagnostics, required for containers)."""
        start = time.perf_counter()
        docker_path = shutil.which("docker")
        duration = (time.perf_counter() - start) * 1000
        if docker_path:
            return ProbeResult(
                probe_id="preflight_docker_client",
                name="Docker Client Tooling",
                category="system",
                status=CheckStatus.PASS,
                duration_ms=duration,
                details={"path": docker_path, "optional": True},
            )
        return ProbeResult(
            probe_id="preflight_docker_client",
            name="Docker Client Tooling",
            category="system",
            status=CheckStatus.INCONCLUSIVE,
            duration_ms=duration,
            details={"optional": True},
            error_message="Docker client not found in PATH. (Optional: required only for Docker adapter mode).",
        )

    def check_report_storage(self) -> ProbeResult:
        """Ensures the report directory is writable."""
        start = time.perf_counter()
        try:
            self.report_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            test_file = self.report_dir / ".write_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            duration = (time.perf_counter() - start) * 1000
            return ProbeResult(
                probe_id="preflight_report_storage",
                name="Report Directory Permissions",
                category="system",
                status=CheckStatus.PASS,
                duration_ms=duration,
                details={"path": str(self.report_dir)},
            )
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return ProbeResult(
                probe_id="preflight_report_storage",
                name="Report Directory Permissions",
                category="system",
                status=CheckStatus.FAIL,
                duration_ms=duration,
                details={"path": str(self.report_dir)},
                error_code=ErrorCode.UNKNOWN_ERROR,
                error_message=f"Report directory is not writable: {e}",
            )

    def run_all(self) -> ReportModel:
        """Executes all preflight checks and produces a ReportModel."""
        start_time = time.perf_counter()
        probes = [
            self.check_python_version(),
            self.check_os_environment(),
            self.check_ssh_client(),
            self.check_docker_client(),
            self.check_report_storage(),
        ]
        duration_sec = time.perf_counter() - start_time
        report = ReportModel(
            test_phase=TestPhase.PREFLIGHT,
            status=CheckStatus.PASS,
            results=probes,
            environment={
                "os": platform.system(),
                "arch": platform.machine(),
                "python": sys.version.split()[0],
            },
        )
        report.compute_summary(duration_sec)
        return report
