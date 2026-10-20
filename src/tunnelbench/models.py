"""Data models and type definitions for TunnelBench."""

from __future__ import annotations

import enum
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid


class CheckStatus(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_RUN = "NOT_RUN"


class TestPhase(str, enum.Enum):
    PREFLIGHT = "preflight"
    BASELINE = "baseline"
    ADAPTER_DEPLOY = "adapter_deploy"
    CLIENT_CHECK = "client_check"
    TARGET_CHECK = "target_check"
    FULL_PIPELINE = "full_pipeline"


class AdapterStatus(str, enum.Enum):
    SUPPORTED = "SUPPORTED"
    EXPERIMENTAL = "EXPERIMENTAL"
    PLANNED = "PLANNED"
    DEPRECATED = "DEPRECATED"


class ErrorCode(str, enum.Enum):
    NONE = "NONE"
    DNS_BOGON_INJECTED = "DNS_BOGON_INJECTED"
    DNS_NXDOMAIN = "DNS_NXDOMAIN"
    DNS_TIMEOUT = "DNS_TIMEOUT"
    TCP_TIMEOUT = "TCP_TIMEOUT"
    TCP_RESET = "TCP_RESET"
    TLS_SNI_BLOCKED = "TLS_SNI_BLOCKED"
    TLS_CERT_INVALID = "TLS_CERT_INVALID"
    TLS_TIMEOUT = "TLS_TIMEOUT"
    HTTP_AUTH_REQUIRED = "HTTP_AUTH_REQUIRED"
    HTTP_GEO_RESTRICTED = "HTTP_GEO_RESTRICTED"
    TARGET_NETWORK_TIMEOUT = "TARGET_NETWORK_TIMEOUT"
    SSH_HOST_KEY_MISMATCH = "SSH_HOST_KEY_MISMATCH"
    SSH_AUTH_FAILED = "SSH_AUTH_FAILED"
    SSH_TIMEOUT = "SSH_TIMEOUT"
    SERVICE_INACTIVE = "SERVICE_INACTIVE"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass
class VPSProfile:
    name: str
    host: str
    port: int = 22
    user: str = "root"
    auth_method: str = "key"  # 'key' or 'agent'
    key_path: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "auth_method": self.auth_method,
            "key_path": self.key_path,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VPSProfile:
        return cls(
            name=data["name"],
            host=data["host"],
            port=int(data.get("port", 22)),
            user=data.get("user", "root"),
            auth_method=data.get("auth_method", "key"),
            key_path=data.get("key_path"),
            tags=list(data.get("tags", [])),
        )


@dataclass
class ProbeResult:
    probe_id: str
    name: str
    category: str  # 'dns', 'tcp', 'tls', 'system', 'http', 'api', 'health'
    status: CheckStatus
    target: str = ""
    duration_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    error_code: ErrorCode = ErrorCode.NONE
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "probe_id": self.probe_id,
            "name": self.name,
            "category": self.category,
            "target": self.target,
            "status": self.status.value,
            "duration_ms": round(self.duration_ms, 2),
            "details": self.details,
            "error_code": self.error_code.value,
            "error_message": self.error_message,
        }


@dataclass
class TestSummary:
    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    inconclusive: int = 0
    not_run: int = 0
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_checks": self.total_checks,
            "passed": self.passed,
            "failed": self.failed,
            "inconclusive": self.inconclusive,
            "not_run": self.not_run,
            "duration_seconds": round(self.duration_seconds, 2),
        }


@dataclass
class ReportModel:
    test_phase: TestPhase
    status: CheckStatus
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: str = "1.0.0"
    timestamp_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    tool_version: str = "0.1.0"
    vps_profile: Optional[Dict[str, Any]] = None
    environment: Dict[str, Any] = field(default_factory=dict)
    adapter: Optional[Dict[str, Any]] = None
    redaction_applied: bool = True
    summary: TestSummary = field(default_factory=TestSummary)
    results: List[ProbeResult] = field(default_factory=list)

    def compute_summary(self, duration_sec: float = 0.0) -> None:
        passed = sum(1 for r in self.results if r.status == CheckStatus.PASS)
        failed = sum(1 for r in self.results if r.status == CheckStatus.FAIL)
        inconclusive = sum(1 for r in self.results if r.status == CheckStatus.INCONCLUSIVE)
        not_run = sum(1 for r in self.results if r.status == CheckStatus.NOT_RUN)
        self.summary = TestSummary(
            total_checks=len(self.results),
            passed=passed,
            failed=failed,
            inconclusive=inconclusive,
            not_run=not_run,
            duration_seconds=duration_sec,
        )
        if failed > 0:
            self.status = CheckStatus.FAIL
        elif inconclusive > 0 and passed == 0:
            self.status = CheckStatus.INCONCLUSIVE
        elif passed > 0:
            self.status = CheckStatus.PASS
        else:
            self.status = CheckStatus.NOT_RUN

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "schema_version": self.schema_version,
            "timestamp_utc": self.timestamp_utc,
            "tool_version": self.tool_version,
            "test_phase": self.test_phase.value,
            "status": self.status.value,
            "vps_profile": self.vps_profile,
            "environment": self.environment,
            "adapter": self.adapter,
            "redaction_applied": self.redaction_applied,
            "summary": self.summary.to_dict(),
            "results": [r.to_dict() for r in self.results],
        }


@dataclass
class DeploymentPlan:
    adapter_name: str
    target_vps: str
    actions: List[str]
    exposed_ports: List[int]
    container_image: Optional[str] = None
    config_path: Optional[str] = None
    system_privileges_required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
