"""Safe SSH Client for Remote Operations.

Enforces strict host key verification, bounded subprocess execution,
and argument arrays to eliminate shell injection vulnerabilities.
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from typing import List, Optional

from tunnelbench.models import ErrorCode, VPSProfile
from tunnelbench.redaction import redact


@dataclass
class SSHResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    error_code: ErrorCode = ErrorCode.NONE
    error_message: str = ""

    @property
    def success(self) -> bool:
        return self.exit_code == 0


class SSHClient:
    """Subprocess-based OpenSSH runner adhering to strict security constraints."""

    def __init__(
        self,
        profile: VPSProfile,
        timeout_seconds: int = 20,
        max_output_bytes: int = 512 * 1024,
    ) -> None:
        self.profile = profile
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes

    def _build_ssh_base_command(self) -> List[str]:
        """Constructs safe OpenSSH command prefix."""
        cmd = [
            "ssh",
            "-p", str(self.profile.port),
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=yes",
            "-o", "ConnectTimeout=10",
        ]

        if self.profile.auth_method == "key" and self.profile.key_path:
            expanded_key = os.path.expanduser(self.profile.key_path)
            cmd.extend(["-i", expanded_key])

        target = f"{self.profile.user}@{self.profile.host}"
        cmd.append(target)
        return cmd

    def run_command(self, remote_command: str) -> SSHResult:
        """Executes a single remote command over SSH with strict timeouts and output capture."""
        cmd = self._build_ssh_base_command()
        cmd.append(remote_command)

        start_time = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            duration_ms = (time.perf_counter() - start_time) * 1000

            stdout = proc.stdout[: self.max_output_bytes]
            stderr = proc.stderr[: self.max_output_bytes]

            error_code = ErrorCode.NONE
            error_message = ""

            if proc.returncode != 0:
                err_lower = stderr.lower()
                if "host key verification failed" in err_lower or "remote host identification has changed" in err_lower:
                    error_code = ErrorCode.SSH_HOST_KEY_MISMATCH
                    error_message = "Host key verification failed. Target VPS host key is unknown or changed."
                elif "permission denied" in err_lower:
                    error_code = ErrorCode.SSH_AUTH_FAILED
                    error_message = "SSH authentication failed (public key rejected)."
                elif "connection timed out" in err_lower or "network is unreachable" in err_lower:
                    error_code = ErrorCode.SSH_TIMEOUT
                    error_message = "SSH connection timed out or network is unreachable."
                else:
                    error_code = ErrorCode.UNKNOWN_ERROR
                    error_message = f"Command failed with exit code {proc.returncode}"

            return SSHResult(
                exit_code=proc.returncode,
                stdout=redact(stdout),
                stderr=redact(stderr),
                duration_ms=duration_ms,
                error_code=error_code,
                error_message=error_message,
            )

        except subprocess.TimeoutExpired:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return SSHResult(
                exit_code=-1,
                stdout="",
                stderr="SSH operation timed out.",
                duration_ms=duration_ms,
                error_code=ErrorCode.SSH_TIMEOUT,
                error_message=f"SSH operation exceeded {self.timeout_seconds}s timeout.",
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return SSHResult(
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_ms=duration_ms,
                error_code=ErrorCode.UNKNOWN_ERROR,
                error_message=f"Unexpected SSH invocation error: {redact(str(e))}",
            )
