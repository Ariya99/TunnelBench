# Protocol Adapters & Implementation Specifications

**Document Status:** Technical Specification  
**Current Release:** TunnelBench 0.1.0  

---

## 1. Candidate Protocol Evaluation

| Protocol / Stack | TunnelBench Status | Implementation State | Deployment Method | Censorship Resistance Hypothesis | Description & Evaluation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Xray VLESS-REALITY (Vision)** | **EXPERIMENTAL** | Implemented (v0.1.0) | Docker (Pinned) | High | Impersonates legitimate decoy TLS servers. Tested with unit mocks; awaiting live VPS and field verification. |
| **SSH Dynamic SOCKS5** | **EXPERIMENTAL** | Implemented (v0.1.0) | Native (OpenSSH) | Low - Medium | Diagnostic baseline using standard OpenSSH client `-D` proxy. Throttled under sustained traffic, but useful for baseline comparison. |
| **Trojan / Trojan-Go** | **PLANNED** | Not Implemented | Docker | Medium | Masquerades as HTTPS. Requires valid TLS domain & certificate registration, increasing operational complexity. |
| **Shadowsocks 2022** | **PLANNED** | Not Implemented | Docker | Medium - Low | Modern AEAD ciphers with improved replay protection. Susceptible to UDP dropping on mobile operators. |
| **Standard WireGuard** | **PLANNED** | Not Implemented | Docker / Kernel | Low | Fixed UDP handshake headers (`0x01...`) often flagged by DPI. Included purely as a contrast probe. |
| **OpenVPN (TCP/UDP)** | **PLANNED** | Not Implemented | Docker | Low | Standard TLS handshake signatures matched by state DPI middleboxes. Upstream project active; planned as contrast baseline. |

---

## 2. Release Status Taxonomy

TunnelBench adheres to strict evidence-based status definitions:

* **`PLANNED`**: Candidate is researched and architectural requirements defined, but no code is yet implemented in TunnelBench.
* **`EXPERIMENTAL`**: Adapter is implemented in TunnelBench and unit-tested with mocks, but has not completed end-to-end verification across live foreign VPS servers and actual Iranian retail networks.
* **`SUPPORTED`**: Adapter has passed all four documented verification criteria:
  1. Full lifecycle implementation (prerequisites, planning, deployment, health check, cleanup).
  2. Complete unit test coverage with zero security regressions.
  3. Live foreign VPS verification on Debian/Ubuntu infrastructure.
  4. Client-side validation verified on at least one operational restricted network.

In release v0.1.0, both `xray-reality` and `ssh-socks` are classified as **EXPERIMENTAL**.

---

## 3. Adapter Lifecycle Contract

All TunnelBench protocol adapters implement the `BaseAdapter` interface:

```text
+-------------------------------------------------------------+
|                        BaseAdapter                          |
+-------------------------------------------------------------+
| 1. check_prerequisites(vps) -> List[CheckResult]            |
| 2. build_deployment_plan(vps, config) -> DeploymentPlan     |
| 3. require_user_approval(plan) -> bool                      |
| 4. deploy(vps, plan) -> DeploymentResult                    |
| 5. health_check(vps) -> List[CheckResult]                   |
| 6. emit_client_config(vps) -> ClientProfile                 |
| 7. cleanup(vps) -> CleanupResult                            |
+-------------------------------------------------------------+
```

---

## 4. Implemented Adapter 1: Xray VLESS-REALITY with XTLS-Vision (EXPERIMENTAL)

### 4.1 Overview
* **Adapter Name:** `xray-reality`
* **Status:** `EXPERIMENTAL` (Implemented & Unit-Tested; Pending live-server and Iranian ISP field measurement)
* **Maintainer:** XTLS / Project X
* **Target Container Image:** `ghcr.io/xtls/xray-core:v1.8.24` (pinned)
* **Default Port:** `443/tcp`
* **Default Decoy Target:** `www.microsoft.com:443` (configurable)

### 4.2 Prerequisites
1. Linux foreign VPS running 64-bit architecture (`x86_64` or `aarch64`).
2. Docker Engine installed and active (`docker ps` returns 0).
3. Inbound traffic allowed on port 443 (or custom port) on VPS firewall.

### 4.3 Deployment Plan
1. Validate port number (1–65535) and decoy SNI hostname.
2. Generate Curve25519 keypair locally or via `xray x25519`.
3. Generate secure UUIDv4 client identifier.
4. Base64-encode server configuration payload to prevent heredoc/shell escaping vulnerabilities.
5. Write server config to `/etc/tunnelbench/xray-reality.json` with `0600` permissions.
6. Execute Docker container run with dropped capabilities and resource limits:
   ```bash
   docker run -d \
     --name tunnelbench-xray-reality \
     --restart unless-stopped \
     -p 443:443/tcp \
     --cap-drop=ALL \
     --cap-add=NET_BIND_SERVICE \
     --security-opt no-new-privileges:true \
     --memory=512m \
     --cpus=1.0 \
     -v /etc/tunnelbench/xray-reality.json:/etc/xray/config.json:ro \
     ghcr.io/xtls/xray-core:v1.8.24 run -config /etc/xray/config.json
   ```

### 4.4 Server-Side Health Checks
- Verify container status (`docker inspect -f '{{.State.Running}}' tunnelbench-xray-reality`).
- Verify listening socket (`ss -tlpn | grep -w ':443'`).
- Redact and inspect last 20 lines of container logs for startup errors.

### 4.5 Cleanup Actions
- Stop container: `docker stop tunnelbench-xray-reality`
- Remove container: `docker rm tunnelbench-xray-reality`
- Remove configuration: `rm -f /etc/tunnelbench/xray-reality.json`

---

## 5. Implemented Adapter 2: SSH SOCKS5 Diagnostic Tunnel (EXPERIMENTAL)

### 5.1 Overview
* **Adapter Name:** `ssh-socks`
* **Status:** `EXPERIMENTAL` (Implemented & Unit-Tested)
* **Mechanism:** OpenSSH dynamic application-level forwarding (`ssh -N -D 127.0.0.1:10808 -p <port> <user>@<host>`).
* **Purpose:** Provides an immediate, zero-installation baseline proxy through the foreign VPS to contrast directly against custom obfuscated tunnels.
