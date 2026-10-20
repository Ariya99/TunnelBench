# Protocol Adapters & Implementation Specifications

**Document Status:** Technical Specification  
**Current Release:** TunnelBench 0.1.0  

---

## 1. Candidate Protocol Evaluation

| Protocol / Stack | Implementation Status | Deployment Method | Censorship Resistance Rating | Description & Evaluation |
| :--- | :--- | :--- | :--- | :--- |
| **Xray VLESS-REALITY (Vision)** | **SUPPORTED** | Docker / Native | **High** | Eliminates TLS-in-TLS signature via zero-copy splice and decoy server impersonation. Tested and maintained by XTLS community. |
| **SSH Dynamic SOCKS5** | **SUPPORTED** | Native (OpenSSH) | **Low - Medium** | Diagnostic baseline using standard OpenSSH client `-D` proxy. Throttled under sustained traffic, but useful for baseline comparison. |
| **Trojan / Trojan-Go** | **PLANNED** | Docker | **Medium** | Masquerades as HTTPS. Requires valid TLS domain & certificate registration, increasing operational complexity. |
| **Shadowsocks 2022** | **EXPERIMENTAL** | Docker | **Medium - Low** | Modern AEAD ciphers with improved replay protection. Susceptible to UDP dropping on mobile operators. |
| **Standard WireGuard** | **EXPERIMENTAL** | Docker / Kernel | **Very Poor** | Fixed UDP handshake headers (`0x01...`) are identified and dropped within milliseconds by Iranian DPI. Included purely as a contrast probe. |
| **OpenVPN** | **DEPRECATED** | Docker | **Very Poor** | Legacy TLS handshake signatures easily matched and terminated by state-level filtering. Deprecated for bypass use. |

---

## 2. Adapter Lifecycle Contract

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

## 3. Supported Adapter 1: Xray VLESS-REALITY with XTLS-Vision

### 3.1 Overview
* **Adapter Name:** `xray-reality`
* **Status:** `SUPPORTED`
* **Maintainer:** XTLS / Project X
* **Target Container Image:** `ghcr.io/xtls/xray-core:v1.8.24` (pinned)
* **Default Port:** `443/tcp`
* **Default Decoy Target:** `www.microsoft.com:443` (configurable)

### 3.2 Prerequisites
1. Linux foreign VPS running 64-bit architecture (`x86_64` or `aarch64`).
2. Docker Engine installed and active (`docker ps` returns 0).
3. Inbound traffic allowed on port 443 (or custom port) on VPS firewall.

### 3.3 Deployment Plan
1. Generate Curve25519 keypair locally or via `xray x25519`.
2. Generate secure UUIDv4 client identifier.
3. Generate server configuration JSON (`/etc/tunnelbench/xray-reality.json`).
4. Execute Docker container run:
   ```bash
   docker run -d \
     --name tunnelbench-xray-reality \
     --restart unless-stopped \
     --network host \
     -v /etc/tunnelbench/xray-reality.json:/etc/xray/config.json:ro \
     ghcr.io/xtls/xray-core:v1.8.24 run -config /etc/xray/config.json
   ```

### 3.4 Server-Side Health Checks
- Verify container status (`docker inspect -f '{{.State.Status}}' tunnelbench-xray-reality`).
- Verify listening socket (`ss -tulpn | grep :443`).
- Redact and inspect last 20 lines of container logs for startup errors.

### 3.5 Cleanup Actions
- Stop container: `docker stop tunnelbench-xray-reality`
- Remove container: `docker rm tunnelbench-xray-reality`
- Remove configuration: `rm -f /etc/tunnelbench/xray-reality.json`

---

## 4. Supported Adapter 2: SSH SOCKS5 Diagnostic Tunnel

### 4.1 Overview
* **Adapter Name:** `ssh-socks`
* **Status:** `SUPPORTED`
* **Mechanism:** OpenSSH dynamic application-level forwarding (`ssh -N -D 127.0.0.1:10808 -p <port> <user>@<host>`).
* **Purpose:** Provides an immediate, zero-installation baseline proxy through the foreign VPS to contrast directly against custom obfuscated tunnels.
