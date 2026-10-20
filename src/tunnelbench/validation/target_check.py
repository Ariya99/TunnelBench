"""Phase 7: Target-Service Validation (Google AI Studio / Gemini API & General HTTPS).

Distinguishes between transport-level reachability, regional restrictions,
and application-level authentication states without requiring sensitive credentials.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.request

from tunnelbench.models import CheckStatus, ErrorCode, ProbeResult, ReportModel, TestPhase
from tunnelbench.redaction import redact


GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"
AI_STUDIO_WEB_ENDPOINT = "https://aistudio.google.com"
CLOUDFLARE_TRACE_ENDPOINT = "https://www.cloudflare.com/cdn-cgi/trace"


class TargetServiceValidator:
    """Validates availability of specific destinations, notably Google AI Studio."""

    def __init__(
        self,
        proxy_url: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        timeout: float = 8.0,
    ) -> None:
        self.proxy_url = proxy_url
        self.gemini_api_key = gemini_api_key
        self.timeout = timeout

    def _build_opener(self) -> urllib.request.OpenerDirector:
        """Constructs urllib OpenerDirector with optional proxy configuration."""
        handlers: List[Any] = []
        if self.proxy_url:
            handlers.append(
                urllib.request.ProxyHandler({"http": self.proxy_url, "https": self.proxy_url})
            )
        return urllib.request.build_opener(*handlers)

    def check_gemini_api(self) -> ProbeResult:
        """Probes generativelanguage.googleapis.com.

        Returns PASS if HTTP 200 (with key) or HTTP 400 (unauthenticated, proving reachability).
        Detects HTTP 403 geographic restrictions.
        """
        start = time.perf_counter()
        url = GEMINI_API_ENDPOINT
        if self.gemini_api_key:
            url += f"?key={self.gemini_api_key}"

        opener = self._build_opener()
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "TunnelBench/0.1.0 (Testing reachability)",
                "Accept": "application/json",
            },
        )

        try:
            with opener.open(req, timeout=self.timeout) as resp:
                duration = (time.perf_counter() - start) * 1000
                code = resp.getcode()
                return ProbeResult(
                    probe_id="target_gemini_api",
                    name="Google Gemini API Gateway Reachability",
                    category="api",
                    status=CheckStatus.PASS,
                    target=GEMINI_API_ENDPOINT,
                    duration_ms=duration,
                    details={"http_code": code, "authenticated": bool(self.gemini_api_key)},
                )
        except urllib.error.HTTPError as e:
            duration = (time.perf_counter() - start) * 1000
            error_body = ""
            try:
                error_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass

            redacted_body = redact(error_body)

            # HTTP 400 Bad Request indicates reaching Google's API gateway without an API key
            if e.code == 400 and ("API key not valid" in error_body or "API_KEY_INVALID" in error_body):
                return ProbeResult(
                    probe_id="target_gemini_api",
                    name="Google Gemini API Gateway Reachability",
                    category="api",
                    status=CheckStatus.PASS,
                    target=GEMINI_API_ENDPOINT,
                    duration_ms=duration,
                    details={
                        "http_code": 400,
                        "verified_transport": True,
                        "note": "Google API Gateway reached successfully (HTTP 400 expected without API key).",
                    },
                )
            elif e.code == 403:
                # Distinguish geographic block from auth block
                if "location" in error_body.lower() or "region" in error_body.lower():
                    return ProbeResult(
                        probe_id="target_gemini_api",
                        name="Google Gemini API Gateway Reachability",
                        category="api",
                        status=CheckStatus.FAIL,
                        target=GEMINI_API_ENDPOINT,
                        duration_ms=duration,
                        error_code=ErrorCode.HTTP_GEO_RESTRICTED,
                        error_message="HTTP 403 Forbidden: Google AI Studio is unavailable in this VPS egress region.",
                        details={"response_snippet": redacted_body[:200]},
                    )
                return ProbeResult(
                    probe_id="target_gemini_api",
                    name="Google Gemini API Gateway Reachability",
                    category="api",
                    status=CheckStatus.FAIL,
                    target=GEMINI_API_ENDPOINT,
                    duration_ms=duration,
                    error_code=ErrorCode.HTTP_AUTH_REQUIRED,
                    error_message=f"HTTP 403 Forbidden: {redacted_body[:200]}",
                )
            else:
                return ProbeResult(
                    probe_id="target_gemini_api",
                    name="Google Gemini API Gateway Reachability",
                    category="api",
                    status=CheckStatus.FAIL,
                    target=GEMINI_API_ENDPOINT,
                    duration_ms=duration,
                    error_code=ErrorCode.UNKNOWN_ERROR,
                    error_message=f"HTTP Error {e.code}: {redacted_body[:200]}",
                )
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return ProbeResult(
                probe_id="target_gemini_api",
                name="Google Gemini API Gateway Reachability",
                category="api",
                status=CheckStatus.FAIL,
                target=GEMINI_API_ENDPOINT,
                duration_ms=duration,
                error_code=ErrorCode.TARGET_NETWORK_TIMEOUT,
                error_message=f"Network connection failed: {redact(str(e))}",
            )

    def check_aistudio_web(self) -> ProbeResult:
        """Probes aistudio.google.com web application landing."""
        start = time.perf_counter()
        opener = self._build_opener()
        req = urllib.request.Request(
            AI_STUDIO_WEB_ENDPOINT,
            headers={"User-Agent": "TunnelBench/0.1.0"},
        )

        try:
            with opener.open(req, timeout=self.timeout) as resp:
                duration = (time.perf_counter() - start) * 1000
                code = resp.getcode()
                return ProbeResult(
                    probe_id="target_aistudio_web",
                    name="Google AI Studio Web Application",
                    category="http",
                    status=CheckStatus.PASS,
                    target=AI_STUDIO_WEB_ENDPOINT,
                    duration_ms=duration,
                    details={"http_code": code},
                )
        except urllib.error.HTTPError as e:
            duration = (time.perf_counter() - start) * 1000
            if e.code in (200, 301, 302):
                return ProbeResult(
                    probe_id="target_aistudio_web",
                    name="Google AI Studio Web Application",
                    category="http",
                    status=CheckStatus.PASS,
                    target=AI_STUDIO_WEB_ENDPOINT,
                    duration_ms=duration,
                    details={"http_code": e.code},
                )
            return ProbeResult(
                probe_id="target_aistudio_web",
                name="Google AI Studio Web Application",
                category="http",
                status=CheckStatus.FAIL,
                target=AI_STUDIO_WEB_ENDPOINT,
                duration_ms=duration,
                error_code=ErrorCode.UNKNOWN_ERROR,
                error_message=f"HTTP Error {e.code}",
            )
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return ProbeResult(
                probe_id="target_aistudio_web",
                name="Google AI Studio Web Application",
                category="http",
                status=CheckStatus.FAIL,
                target=AI_STUDIO_WEB_ENDPOINT,
                duration_ms=duration,
                error_code=ErrorCode.TARGET_NETWORK_TIMEOUT,
                error_message=f"Network connection failed: {redact(str(e))}",
            )

    def check_general_https(self) -> ProbeResult:
        """Probes reference public endpoint (Cloudflare trace) to confirm general web reachability."""
        start = time.perf_counter()
        opener = self._build_opener()
        req = urllib.request.Request(
            CLOUDFLARE_TRACE_ENDPOINT,
            headers={"User-Agent": "TunnelBench/0.1.0"},
        )

        try:
            with opener.open(req, timeout=self.timeout) as resp:
                duration = (time.perf_counter() - start) * 1000
                code = resp.getcode()
                body = resp.read().decode("utf-8", errors="replace")
                details: Dict[str, Any] = {"http_code": code}
                for line in body.splitlines():
                    if line.startswith("ip=") or line.startswith("loc=") or line.startswith("colo="):
                        k, v = line.split("=", 1)
                        details[k] = v

                return ProbeResult(
                    probe_id="target_general_https",
                    name="General HTTPS Web Reachability",
                    category="http",
                    status=CheckStatus.PASS,
                    target=CLOUDFLARE_TRACE_ENDPOINT,
                    duration_ms=duration,
                    details=details,
                )
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return ProbeResult(
                probe_id="target_general_https",
                name="General HTTPS Web Reachability",
                category="http",
                status=CheckStatus.FAIL,
                target=CLOUDFLARE_TRACE_ENDPOINT,
                duration_ms=duration,
                error_code=ErrorCode.TARGET_NETWORK_TIMEOUT,
                error_message=f"General HTTPS request failed: {redact(str(e))}",
            )

    def run_all(self, target: str = "all") -> ReportModel:
        """Runs requested target validations."""
        start_time = time.perf_counter()
        results: List[ProbeResult] = []

        if target in ("all", "gemini"):
            results.append(self.check_gemini_api())
            results.append(self.check_aistudio_web())

        if target in ("all", "https"):
            results.append(self.check_general_https())

        duration_sec = time.perf_counter() - start_time
        report = ReportModel(
            test_phase=TestPhase.TARGET_CHECK,
            status=CheckStatus.PASS,
            details={"proxy": self.proxy_url, "target_profile": target},
            results=results,
        )
        report.compute_summary(duration_sec)
        return report
