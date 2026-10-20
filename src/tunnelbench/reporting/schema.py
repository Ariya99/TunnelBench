"""JSON Schema Specification and Validator for TunnelBench Reports."""

from __future__ import annotations

from typing import Any, Dict


SCHEMA_VERSION = "1.0.0"

REPORT_JSON_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "TunnelBenchReport",
    "version": SCHEMA_VERSION,
    "type": "object",
    "required": [
        "run_id",
        "schema_version",
        "timestamp_utc",
        "tool_version",
        "test_phase",
        "status",
        "redaction_applied",
        "results",
    ],
    "properties": {
        "run_id": {"type": "string"},
        "schema_version": {"type": "string", "enum": [SCHEMA_VERSION]},
        "timestamp_utc": {"type": "string"},
        "tool_version": {"type": "string"},
        "test_phase": {"type": "string"},
        "status": {"type": "string", "enum": ["PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN"]},
        "vps_profile": {"type": ["object", "null"]},
        "environment": {"type": "object"},
        "adapter": {"type": ["object", "null"]},
        "redaction_applied": {"type": "boolean"},
        "summary": {"type": "object"},
        "results": {"type": "array"},
    },
}
