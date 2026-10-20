# Testing from Iranian Networks: Methodological Guide

**Target Audience:** Network Engineers, System Administrators, and Researchers evaluating reachability from Iranian retail and enterprise networks.

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

Filtering behavior is not uniform across Iran. It varies by operator type, upstream transit paths, province, and time of day. When conducting tests with TunnelBench, always record your access network context:

| ISP / Operator | Access Type | Network Profile | Reported Observations & Test Hypotheses |
| :--- | :--- | :--- | :--- |
| **MCI (Hamrah-e Aval)** | Mobile | Large mobile subscriber base, CGNAT | High UDP packet drop rates reported during peak hours; SNI-targeted throttling observed in OONI data. |
| **Irancell (MTN)** | Mobile | Dual-stack IPv6/IPv4, widespread coverage | Active probing on unknown TLS endpoints reported; heuristic throttling on single-flow sustained throughput. |
| **Rightel** | Mobile | Third mobile carrier footprint | Variable routing; generally follows national TIC upstream filtering baseline. |
| **Mokhaberat (TCI)** | Fixed-line DSL/FTTH | Incumbent fixed-line carrier | High rate of DNS redirection to bogon addresses (`10.10.34.35` / `10.10.34.0/24`) documented in OONI telemetry. |
| **Shatel / Pars Online / Asiatech** | Fixed-line Private ISPs | Commercial ADSL, VDSL, FTTH | Lower domestic latency; upstream transit routes via TIC gateway middleboxes. |
| **Zitel** | Fixed Wireless (TD-LTE) | Urban fixed wireless | Bandwidth shaping and elevated latency reported during evening peak usage windows (19:00 - 23:30). |

*Note:* These patterns represent empirical hypotheses to measure, not guaranteed permanent behaviors across every individual connection.

---

## 3. Step-by-Step Testing Procedure

### Step 1: Document Your Environment
Identify and record your network context. Run:
```bash
tunnelbench client-check \
  --profile <profile-name> \
  --isp "Irancell" \
  --connection-type "mobile" \
  --region "Tehran"
```
*Note:* TunnelBench does not attempt to infer or expose your exact location; tags are stored locally for comparison.

### Step 2: Test Direct Reachability (Phase 6.1 - 6.3)
1. **DNS Integrity Check:**
   - Resolve your VPS hostname (if using FQDN) through local DNS.
   - If the returned IP matches `10.10.34.x` or `127.0.0.1`, DNS tampering is confirmed.
   - Mitigation: Use direct IP or DNS over HTTPS (DoH) via verified clean resolvers.
2. **TCP Port Reachability:**
   - Send TCP SYN packets to the destination port (e.g., 443, 8443, 22).
   - If `SYN-ACK` returns in normal RTT (typically 80–180ms to Europe), transport is open.
   - If connections time out consistently, the destination IP or port is blocked or dropped upstream.
   - If a `RST` is returned in < 30ms, gateway DPI injection is the likely cause.

### Step 3: Validate Protocol Handshake (Phase 6.4)
- Initiate the TLS handshake using the configured decoy domain (for VLESS-REALITY).
- Observe whether the handshake completes within 1.5x of base TCP RTT.
- If the TCP connection established but TLS handshake timed out or was reset, the decoy SNI is filtered or the TLS fingerprint was flagged by local DPI.

### Step 4: Validate In-Tunnel Forwarding (Phase 6.5 - 6.7)
- Bind the local proxy client (e.g., SOCKS5 on `127.0.0.1:10808` or HTTP on `127.0.0.1:10809`).
- Execute HTTP `GET` requests to a standard public baseline: `https://www.cloudflare.com/cdn-cgi/trace` or `https://httpbin.org/ip`.
- Verify the outbound IP matches your foreign VPS IP, not your domestic ISP IP.

### Step 5: Validate Target Service (Phase 7: Google AI Studio / Gemini)
- Execute `tunnelbench target-check --target gemini --proxy socks5://127.0.0.1:10808`
- Verify that `generativelanguage.googleapis.com` responds with HTTP 400 (if unauthenticated) or HTTP 200 (if API key provided).
- Verify that `aistudio.google.com` returns HTTP 200/302.

### Step 6: Longitudinal Stability Testing (Phase 8)
- Run repeated tests over 10 to 30 iterations spaced across different hours.
- Record the **Survival Rate**: What percentage of attempts succeed without interruption?
- Record **Jitter and Throttling**: Does latency stay consistent, or does throughput degrade after sustained transfer?

---

## 4. Safety and Prudence

1. **No Port Scanning:** TunnelBench never performs port sweeps across IP ranges. It tests exclusively the specific destination port configured by the user.
2. **No High-Volume Flooding:** Tests use small, bounded HTTP request bodies to measure latency and availability, preventing unnecessary bandwidth strain.
3. **Local Storage Only:** Reports are saved solely on your local laptop machine in standard JSON and CSV format.
