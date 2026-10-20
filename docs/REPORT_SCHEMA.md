# TunnelBench Report Schema Specification

**Schema Version:** `1.0.0`  
**Standard Formats:** JSON (Hierarchical) and CSV (Row-per-Probe / Row-per-Attempt)  

---

## 1. Top-Level JSON Schema (`TunnelBenchReport_v1`)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "TunnelBenchReport",
  "version": "1.0.0",
  "type": "object",
  "required": [
    "run_id",
    "schema_version",
    "timestamp_utc",
    "tool_version",
    "test_phase",
    "status",
    "redaction_applied",
    "results"
  ],
  "properties": {
    "run_id": { "type": "string", "description": "Unique UUIDv4 identifying this test run" },
    "schema_version": { "type": "string", "enum": ["1.0.0"] },
    "timestamp_utc": { "type": "string", "format": "date-time" },
    "tool_version": { "type": "string" },
    "vps_profile": {
      "type": "object",
      "properties": {
        "name": { "type": "string" },
        "host": { "type": "string" },
        "port": { "type": "integer" },
        "user": { "type": "string" },
        "auth_method": { "type": "string" }
      }
    },
    "environment": {
      "type": "object",
      "properties": {
        "client_os": { "type": "string" },
        "client_python": { "type": "string" },
        "isp": { "type": "string" },
        "connection_type": { "type": "string", "enum": ["mobile", "fixed", "unknown"] },
        "region": { "type": "string" }
      }
    },
    "test_phase": {
      "type": "string",
      "enum": [
        "preflight",
        "baseline",
        "adapter_deploy",
        "client_check",
        "target_check",
        "full_pipeline"
      ]
    },
    "adapter": {
      "type": "object",
      "properties": {
        "name": { "type": "string" },
        "version": { "type": "string" },
        "mode": { "type": "string" }
      }
    },
    "status": {
      "type": "string",
      "enum": ["PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN"]
    },
    "redaction_applied": { "type": "boolean" },
    "summary": {
      "type": "object",
      "properties": {
        "total_checks": { "type": "integer" },
        "passed": { "type": "integer" },
        "failed": { "type": "integer" },
        "inconclusive": { "type": "integer" },
        "not_run": { "type": "integer" },
        "duration_seconds": { "type": "number" }
      }
    },
    "results": {
      "type": "array",
      "items": { "$ref": "#/$defs/ProbeResult" }
    }
  },
  "$defs": {
    "ProbeResult": {
      "type": "object",
      "required": ["probe_id", "name", "category", "status", "duration_ms"],
      "properties": {
        "probe_id": { "type": "string" },
        "name": { "type": "string" },
        "category": {
          "type": "string",
          "enum": ["dns", "tcp", "tls", "system", "http", "api", "health"]
        },
        "target": { "type": "string" },
        "status": {
          "type": "string",
          "enum": ["PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN"]
        },
        "duration_ms": { "type": "number" },
        "details": { "type": "object" },
        "error_code": { "type": "string" },
        "error_message": { "type": "string" }
      }
    }
  }
}
```

---

## 2. Granular CSV Layout (Row-per-Probe / Row-per-Attempt)

When exported to CSV, the hierarchical report is flattened so each row represents a discrete measurement probe:

| Column Name | Type | Example | Description |
| :--- | :--- | :--- | :--- |
| `run_id` | string | `7b9f8d12-...` | Unique test run identifier |
| `timestamp_utc` | ISO-8601 | `2026-10-20T10:15:00Z` | Timestamp when test initiated |
| `test_phase` | string | `client_check` | Current lifecycle phase |
| `vps_profile` | string | `hetzner-fsn1` | Name of VPS profile |
| `isp` | string | `Irancell` | Operator / ISP provided or observed |
| `connection_type` | string | `mobile` | Connection access technology |
| `adapter_name` | string | `xray-reality` | Evaluated tunnel adapter |
| `probe_id` | string | `probe_tcp_connect` | Unique identifier of probe |
| `probe_category` | string | `tcp` | Diagnostic domain (`dns`, `tcp`, `tls`, `http`, `api`) |
| `target` | string | `198.51.100.1:443` | Endpoint probed |
| `status` | string | `PASS` | Outcome status |
| `duration_ms` | float | `124.5` | Probe duration in milliseconds |
| `error_code` | string | `NONE` | Categorized error code |
| `error_message` | string | `Connected` | Sanitized / redacted message |

---

## 3. Standardized Error Taxonomy

TunnelBench classifies errors into precise categories to prevent misattribution:

| Error Code | Classification | Meaning |
| :--- | :--- | :--- |
| `DNS_BOGON_INJECTED` | Censorship / Interference | Query returned known poisoned bogon IP (e.g., `10.10.34.35` or `127.0.0.1`). |
| `DNS_NXDOMAIN` | Routing / Misconfig | Hostname could not be found by resolver. |
| `TCP_TIMEOUT` | Routing / Block | SYN packet dropped without response (common when IP/port is dropped). |
| `TCP_RESET` | DPI / Interference | Injected TCP RST received in < 30ms before true round-trip time. |
| `TLS_SNI_BLOCKED` | DPI / Interference | TLS ClientHello dropped or reset during SNI inspection. |
| `TLS_CERT_INVALID` | Security / MITM | Upstream certificate mismatch or MITM inspection attempted. |
| `HTTP_AUTH_REQUIRED` | Application | Target returned HTTP 401 / 403 API key error (transport is working). |
| `HTTP_GEO_RESTRICTED` | Target Policy | Target returned HTTP 403 with geographic restriction notice. |
| `SSH_HOST_KEY_MISMATCH`| Security Violation | VPS host key changed; connection rejected. |
