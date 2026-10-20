"""Centralized Secret Redaction Engine for TunnelBench.

Ensures that credentials, private keys, tokens, UUIDs, and full connection URIs
are systematically scrubbed before reaching logs, terminal output, or report files.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Union


class RedactionEngine:
    """Detects and replaces sensitive credentials, tokens, and cryptographic keys."""

    # Regex patterns for sensitive values
    _PATTERNS = [
        # PEM Private Keys
        (
            re.compile(
                r"-----BEGIN\s+[A-Z\s]+PRIVATE\s+KEY-----[\s\S]*?-----END\s+[A-Z\s]+PRIVATE\s+KEY-----",
                re.IGNORECASE,
            ),
            "[REDACTED_PRIVATE_KEY]",
        ),
        # Google API Keys (e.g., AIzaSy...)
        (
            re.compile(r"\bAIzaSy[0-9A-Za-z_-]{20,50}\b"),
            "[REDACTED_API_KEY]",
        ),
        # Bearer tokens
        (
            re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
            "Bearer [REDACTED_TOKEN]",
        ),
        # Full proxy connection URIs
        (
            re.compile(r"\bvless://[^\s\"'>]+", re.IGNORECASE),
            "vless://[REDACTED_URI]",
        ),
        (
            re.compile(r"\bvmess://[^\s\"'>]+", re.IGNORECASE),
            "vmess://[REDACTED_URI]",
        ),
        (
            re.compile(r"\bss://[^\s\"'>]+", re.IGNORECASE),
            "ss://[REDACTED_URI]",
        ),
        (
            re.compile(r"\btrojan://[^\s\"'>]+", re.IGNORECASE),
            "trojan://[REDACTED_URI]",
        ),
        # Standard UUIDv4 (used in VLESS, etc.)
        (
            re.compile(
                r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
            ),
            "[REDACTED_UUID]",
        ),
        # Key/Password assignments
        (
            re.compile(r"(?i)(private[_\s-]?key\s*[:=]\s*)[A-Za-z0-9+/_-]{20,}={0,2}"),
            r"\g<1>[REDACTED_KEY]",
        ),
        (
            re.compile(r"(?i)(secret[_\s-]?key\s*[:=]\s*)[A-Za-z0-9+/_-]{16,}={0,2}"),
            r"\g<1>[REDACTED_SECRET]",
        ),
        (
            re.compile(r"(?i)(password\s*[:=]\s*)['\"]?[^\s,;'\"}]+['\"]?"),
            r"\g<1>[REDACTED_PASSWORD]",
        ),
    ]

    @classmethod
    def redact_text(cls, text: str) -> str:
        """Redacts all known sensitive patterns from a string."""
        if not text:
            return ""
        result = text
        for pattern, replacement in cls._PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    @classmethod
    def redact_structure(cls, data: Any) -> Any:
        """Recursively scrubs strings within dicts, lists, and primitives."""
        if isinstance(data, str):
            return cls.redact_text(data)
        elif isinstance(data, dict):
            return {k: cls.redact_structure(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.redact_structure(item) for item in data]
        elif isinstance(data, tuple):
            return tuple(cls.redact_structure(item) for item in data)
        return data


def redact(val: Union[str, Dict[str, Any], List[Any], Any]) -> Any:
    """Convenience helper to redact any object or string."""
    return RedactionEngine.redact_structure(val)
