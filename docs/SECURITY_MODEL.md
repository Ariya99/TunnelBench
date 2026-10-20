# TunnelBench Security Model & Safeguards

**Version:** 1.0.0  
**Security Lead:** Security Architecture & Review Team  

---

## 1. Threat Model & Security Posture

TunnelBench operates in adversarial and monitored network environments. The tool itself must not become a vector for credential compromise, unauthorized access, or unintended disclosure of network telemetry.

### In Scope
- Protection of user authentication credentials (SSH private keys, proxy keys, API tokens).
- Prevention of arbitrary remote code execution on the foreign VPS.
- Prevention of local command injection or shell escapes on the operator's workstation.
- Defense against credential leakage in logs, command histories, exception traces, and reports.
- Protection against Man-in-the-Middle (MITM) attacks during remote SSH administration.

### Out of Scope
- Circumvention of state-level lawful intercept if the operator's machine is physically compromised.
- Cryptanalysis of underlying modern ciphers (X25519, ChaCha20-Poly1305, AES-GCM).

---

## 2. Core Security Safeguards

### 2.1 Strict SSH Host-Key Verification
- Remote operations on the foreign VPS use OpenSSH with `StrictHostKeyChecking=yes`.
- TunnelBench **never** disables host-key checking, never uses `StrictHostKeyChecking=no`, and never sets `UserKnownHostsFile=/dev/null`.
- If a VPS host key has changed or is unknown, OpenSSH halts and TunnelBench surfaces a clear error, requiring the administrator to inspect and verify the fingerprint.

### 2.2 Zero Credential Persistence
- Configuration files (`profiles.json`) store only non-secret connection descriptors:
  - Hostname or IP address
  - Port number
  - Username
  - Path to local public/private key file or indicator to use `ssh-agent`.
- TunnelBench never stores or prompts to save plaintext passwords, SSH private keys, VLESS UUIDs, or REALITY private keys in persistent application configs.
- Ephemeral runtime parameters (such as newly generated REALITY server keys) are passed strictly in-memory during deployment and written to root-restricted paths on the target VPS (`chmod 600`).

### 2.3 Comprehensive Secret Redaction
- All terminal output, log files, exception stack traces, and exported JSON/CSV reports pass through a centralized redaction filter (`tunnelbench.redaction.RedactionEngine`).
- Monitored patterns:
  - Standard UUIDv4 patterns (`[REDACTED_UUID]`)
  - PEM private key blocks (`-----BEGIN ... PRIVATE KEY-----`)
  - Curve25519 / Ed25519 base64 keys
  - API Keys matching patterns like `AIzaSy...` (`[REDACTED_API_KEY]`)
  - Full proxy connection strings containing keys or UUIDs (`vless://[REDACTED_URI]`)
  - Bearer authentication tokens (`Bearer [REDACTED_TOKEN]`)

### 2.4 Injection-Proof Subprocess Execution
- Subprocess invocations on both the local machine and remote host avoid shell expansion:
  - Local commands use direct `subprocess.run(["/usr/bin/ssh", ...], shell=False)`.
  - Remote commands are constructed from static, validated argument arrays.
  - User-supplied inputs (hostnames, ports, usernames, profile names) are validated using strict alphanumeric and regex whitelist checks before use.

### 2.5 Explicit User Approval Gates
- TunnelBench strictly distinguishes between **read-only diagnostic operations** and **mutating deployment/cleanup operations**.
- Before modifying a foreign VPS (e.g., pulling a Docker image, binding ports, creating configuration files, or stopping containers), TunnelBench generates a structured **Deployment Plan** detailing:
  - Files to be created or modified
  - Docker containers to be pulled and started
  - Network ports to be opened
  - System privileges required
- The user must explicitly approve the plan before execution proceeds. In automation mode, an explicit `--yes` flag is required.

### 2.6 Target Endpoint Ethics & Safety
- Target tests for Google AI Studio / Gemini interact exclusively with documented, public API endpoints using standard HTTP requests.
- TunnelBench strictly forbids:
  - Vulnerability scanning or port sweeping
  - High-concurrency denial-of-service traffic
  - Automated CAPTCHA solving or bot evasions
  - Credential stuffing or brute forcing
