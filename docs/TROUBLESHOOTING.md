# Troubleshooting Decision Trees & Diagnostics

This guide provides structured decision trees for diagnosing common failure modes identified during TunnelBench runs.

---

## 1. Remote Foreign VPS Baseline Failures

### Symptom: `SSH_HOST_KEY_MISMATCH` or `SSH_AUTH_FAILED`
```text
Did SSH host key verification fail?
├── YES -> STOP! Has the VPS been reprovisioned or reinstalled?
│          ├── YES: Update your known_hosts: `ssh-keygen -R <host>`
│          └── NO:  CAUTION! Possible Man-in-the-Middle attack or IP hijacking. Do not bypass!
└── NO  -> Verify SSH private key permissions (`chmod 600 ~/.ssh/id_ed25519`)
           and ensure key is loaded in ssh-agent: `ssh-add -l`.
```

### Symptom: VPS Baseline Fails "Outbound DNS / HTTPS"
- **Cause:** The foreign VPS provider itself has restrictive egress firewall rules or local resolv.conf misconfigurations.
- **Resolution:** Verify `/etc/resolv.conf` on the VPS has active nameservers (`nameserver 1.1.1.1` / `8.8.8.8`) and check provider security group outbound rules.

---

## 2. Iranian Client-Side Diagnostic Failures

### Decision Tree: Client Connection Failures
```text
Phase 6: Client Diagnostic
│
├── DNS Resolution Probe
│   ├── Returns 10.10.34.x / 127.0.0.1  -> Error: DNS_BOGON_INJECTED
│   │                                      Fix: Use direct IP or DNS over HTTPS (DoH)
│   └── Times out                       -> Error: DNS_TIMEOUT (UDP 53 blocked)
│
├── TCP Connect Probe
│   ├── Times out (10s - 30s)           -> Error: TCP_TIMEOUT
│   │                                      Diagnosis: VPS IP or Port is routing-blocked by TIC.
│   │                                      Fix: Change port to 443/8443 or change VPS IP.
│   └── Returns RST in < 30ms           -> Error: TCP_RESET
│                                          Diagnosis: Gateway DPI injected reset.
│
├── TLS Probe (REALITY Handshake)
│   ├── TLS Handshake Timeout           -> Decoy SNI blocked or TLS fingerprint flagged.
│   │                                      Fix: Rotate decoy SNI in adapter config.
│   └── Certificate Validation Error    -> Local MITM device intercepted TLS connection.
│
└── Tunnel Forwarding
    ├── SOCKS5 connection refused       -> Local proxy client is not running on 127.0.0.1.
    └── Remote 502/504 Bad Gateway      -> Xray service on VPS is not running or listening.
```

---

## 3. Target Service Failures (Google AI Studio / Gemini)

### Error Matrix
| Observed Status Code | Error Classification | Root Cause & Action |
| :--- | :--- | :--- |
| **Connection Timeout** | `TARGET_NETWORK_TIMEOUT` | Tunnel is not forwarding outbound HTTPS to Google endpoints. Check VPS default route. |
| **HTTP 400 Bad Request** | `PASS` (for probe without key) | Transport succeeded! Google API responded confirming reachability. |
| **HTTP 401 Unauthorized**| `HTTP_AUTH_REQUIRED` | API key provided is invalid or expired. |
| **HTTP 403 Forbidden (Geo)** | `HTTP_GEO_RESTRICTED` | Google AI Studio does not offer service to the IP region of your foreign VPS. Choose another VPS location (e.g. Frankfurt, Zurich, Helsinki). |
| **HTTP 200 OK** | `PASS` | End-to-end transport and authenticated API access fully verified. |
