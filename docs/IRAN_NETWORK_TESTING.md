# Testing from Iranian Networks: Methodological Guide

**Target Audience:** Network Engineers, System Administrators, and Researchers operating within Iranian retail and enterprise networks.

---

## 1. Fundamental Principles

### 1.1 The Cardinal Rule of Remote Measurement
> **A healthy VPS does not imply a reachable tunnel.**

Never assume that because your foreign VPS has 99.99% uptime, 1Gbps bandwidth, and clean outbound routes to Google in Germany or the Netherlands, a user on MCI in Tehran or Shatel in Isfahan can connect to it.

All measurements in TunnelBench are classified along two orthogonal axes:
1. **Infrastructure Health:** Is the foreign server capable of hosting and routing tunnel traffic?
2. **Access Network Reachability:** Does the user's specific access ISP allow packets to reach the foreign VPS, complete handshakes, and forward payload data?

---

## 2. Iranian ISP Landscape & Diversity

Filtering behavior is not uniform across Iran. When conducting tests with TunnelBench, always record your access network context:

| ISP / Operator | Type | Typical Characteristics | Known Filtering Patterns |
| :--- | :--- | :--- | :--- |
| **MCI (Hamrah-e Aval)** | Mobile | High subscriber volume, nationwide CGNAT | Aggressive UDP dropping, rapid SNI throttling, mobile-specific blackouts during unrest. |
| **Irancell (MTN)** | Mobile | Modern IPv6/IPv4 dual-stack, widespread | Active probing on unknown TLS ports, heuristic rate limiting on sustained single-stream connections. |
| **Rightel** | Mobile | Smaller mobile footprint | Variable routing policies, often mirrors MCI baseline. |
| **Mokhaberat (TCI)** | Fixed-line DSL/FTTH | Incumbent state telecom, high latency | Heavy DNS redirection to bogon IPs (`10.10.34.35`), deep packet inspection at provincial gateways. |
| **Shatel / Pars Online / Asiatech** | Fixed-line Private ISPs | Commercial DSL, VDSL, FTTH | Lower internal latency, but strict upstream TIC filtering. Occasionally higher bandwidth allowances before throttling kicks in. |
| **Zitel** | Fixed Wireless (TD-LTE) | Urban fixed wireless | Aggressive traffic shaping during peak evening hours (19:00 - 23:30). |

---

## 3. Step-by-Step Testing Procedure

### Step 1: Pre-Test Documentation
Before running tests, identify your local network context. Run:
```bash
tunnelbench client-check --isp "Irancell" --connection-type "mobile" --region "Tehran"
```
*Note:* TunnelBench does not attempt to guess or expose your exact geo-location; user tags are purely for your own local report comparative analysis.

### Step 2: Test Direct Reachability (Phase 6.1 - 6.3)
1. **DNS Integrity Check:**
   - Resolve your VPS hostname (if using FQDN) through local DNS.
   - If the returned IP matches `10.10.34.x` or `127.0.0.1`, DNS tampering is confirmed.
   - Recommended remedy: Use direct IP or DNS over HTTPS (DoH) via trusted clean resolvers.
2. **TCP Port Reachability:**
   - Send TCP SYN packets to the destination port (e.g., 443, 8443, 22).
   - If `SYN-ACK` returns in normal RTT (typically 80–180ms to Europe), transport is open.
   - If connections time out consistently, the destination IP or port is blocked by TIC/ISP routing tables.
   - If a `RST` is returned in < 25ms, local gateway DPI is injecting TCP resets.

### Step 3: Validate Protocol Handshake (Phase 6.4)
- Initiate the TLS handshake using the configured decoy domain (for VLESS-REALITY).
- Observe whether the handshake completes within 1.5x of base TCP RTT.
- If the TCP connection established but TLS handshake timed out or was reset, the decoy SNI is filtered or the TLS fingerprint was flagged by local DPI.

### Step 4: Validate In-Tunnel Forwarding (Phase 6.5 - 6.7)
- Bind the local proxy client (e.g., SOCKS5 on `127.0.0.1:10808` or HTTP on `127.0.0.1:10809`).
- Execute HTTP `GET` requests to a standard public baseline: `https://www.cloudflare.com/cdn-cgi/trace` or `https://httpbin.org/ip`.
- Verify the outbound IP matches your foreign VPS IP, not your Iranian ISP IP.

### Step 5: Validate Target Service (Phase 7: Google AI Studio / Gemini)
- Execute `tunnelbench target-check --target gemini --proxy socks5://127.0.0.1:10808`
- Verify that `generativelanguage.googleapis.com` responds with HTTP 400 (if unauthenticated) or HTTP 200 (if API key provided).
- Verify that `aistudio.google.com` returns HTTP 200/302.

### Step 6: Longitudinal Stability Testing (Phase 8)
- Run repeated tests over 10 to 30 iterations spaced over 10 minutes.
- Record the **Survival Rate**: What percentage of attempts succeed without interruption?
- Record **Jitter and Throttling**: Does latency stay consistent, or does throughput degrade after 50MB of data transfer?

---

## 4. Safety and Prudence

1. **No Port Scanning:** TunnelBench never performs port sweeps across IP ranges. It tests exclusively the specific destination port configured by the user.
2. **No High-Volume Flooding:** Tests use small, bounded HTTP request bodies to measure latency and availability, preventing unnecessary bandwidth strain.
3. **Local Storage Only:** Reports are saved solely on your local laptop machine in standard JSON and CSV format.
