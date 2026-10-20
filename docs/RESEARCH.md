# TunnelBench Research & Evidence Base

**Document Status:** Living Research Document  
**Last Updated:** October 2026  
**Authors:** Ariya99 & TunnelBench Measurement Engineering Team  

---

## 1. Executive Summary

Network measurement in restrictive jurisdictions cannot treat internet access as a binary connected/disconnected state. In Iran, connectivity is subject to centralized policy enforcement coordinated through the Telecommunication Infrastructure Company (TIC / شرکت ارتباطات زیرساخت), distributed across retail ISPs (e.g., Mobile: Irancell, MCI, Rightel; Fixed-line: Shatel, Mokhaberat/TCI, Asiatech, Pars Online, Zitel).

TunnelBench bridges the gap between server-side infrastructure readiness and client-side reachability by establishing reproducible, hypothesis-driven measurement protocols.

---

## 2. Documented Iranian Filtering Mechanics & Hypotheses

### 2.1 DNS Manipulation & Tampering
* **Mechanism:** DNS requests sent to foreign resolvers (e.g., `8.8.8.8`, `1.1.1.1`) over plain UDP port 53 are routinely intercepted, redirected, or poisoned.
* **Empirical Evidence (OONI Data 2024–2025):** Web Connectivity tests collected across Iranian ASNs demonstrate consistent DNS injection returning private, local IPv4 "bogon" addresses, predominantly within the `10.10.34.0/24` subnet (most frequently `10.10.34.35`), as well as fake `127.0.0.1` responses.
* **Measurement Impact:** Testing tools cannot trust OS-default DNS resolvers for remote endpoints. TunnelBench measures DNS via direct socket resolution, compares against expected IP patterns, and validates DNS over HTTPS (DoH) where applicable.

### 2.2 TCP Resets and Connection Timeouts
* **Mechanism:** Deep Packet Inspection (DPI) equipment deployed at transit gateways and major ISP exchanges inspects TCP handshakes. If a destination IP is graylisted or blacklisted, SYN packets are dropped (inducing timeout) or a spoofed TCP RST packet is injected.
* **Observation:** Outbound TCP connect latency (`SYN` -> `SYN-ACK`) diverges drastically between domestic endpoints (< 15ms) and foreign VPS endpoints (often > 120ms or dropping into 10–30s timeout windows).

### 2.3 TLS SNI Filtering & Handshake Disruption
* **Mechanism:** Plaintext Server Name Indication (SNI) in the `ClientHello` message is parsed by DPI. If the SNI matches a blocked domain pattern, the handshake is aborted via injected RSTs or dropped `ServerHello` packets.
* **Active Probing:** Iranian filtering systems have increasingly implemented active probing mechanisms. When a foreign server accepts TLS handshakes mimicking popular services without completing expected certificate handshakes or when traffic anomalies appear, the foreign IP address is flagged or throttled.

### 2.4 WireGuard and UDP Protocol Throttling
* **Mechanism:** Standard WireGuard uses fixed, identifiable packet header signatures (e.g., initial handshake packet type `0x01` followed by a fixed 3-byte sender index structure).
* **Research Assessment:** Iranian DPI filters reliably classify unmasked WireGuard handshakes within milliseconds, dropping or throttling packets regardless of the destination port. WireGuard without dynamic obfuscation layers (such as AmneziaWG or Shadowsocks wrappers) is classified as **UNSUITABLE** for direct Iran-to-foreign-VPS transit.

### 2.5 VLESS with REALITY and XTLS-Vision
* **Mechanism:** REALITY circumvents TLS-in-TLS identification by acting as a transparent TLS reverse-proxy to a legitimate, unblocked foreign server (decoy SNI, such as trusted CDN or cloud domains). The client sends a genuine TLS `ClientHello` matching the decoy's cipher suites and SNI, while incorporating a short authentication key. If authentication succeeds, Xray intercepts the stream; if an unauthorized active prober probes the server, the connection is passed directly to the genuine decoy server without anomaly.
* **Field Status:** VLESS-REALITY-Vision remains the most resilient direct-connection protocol across Iranian ISPs, though performance varies heavily depending on the choice of decoy SNI, destination ASN, and client ISP throttling thresholds.

---

## 3. Protocol Feasibility & Candidate Matrix

| Candidate | Maintenance Status | Linux VPS Support | Censorship Resistance in Iran | Docker Support | Status in TunnelBench |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Xray VLESS-REALITY (Vision)** | Active (XTLS Community) | Excellent | High (Current industry standard) | Yes (`ghcr.io/xtls/xray-core`) | **SUPPORTED** (MVP Focus) |
| **Trojan-Go / Trojan-GFW** | Minimal / Archived | Good | Medium (Requires domain + valid TLS cert) | Yes | **PLANNED** |
| **Shadowsocks 2022** | Maintained | Excellent | Medium-Low (Susceptible to UDP drop / port block) | Yes | **EXPERIMENTAL** |
| **Standard WireGuard** | Active (Kernel upstream) | Native | Poor (Blocked by handshake signature DPI) | Yes | **EXPERIMENTAL** (Diagnostic only) |
| **OpenVPN (TCP/UDP)** | Active | High | Very Poor (DPI fingerprinting drops handshakes) | Yes | **DEPRECATED** (Baseline contrast only) |
| **SSH Dynamic SOCKS5** | Active (OpenSSH) | Native | Low (Throttling on sustained high throughput) | Native | **SUPPORTED** (Fallback Diagnostic) |

---

## 4. Target Destination Analysis: Google AI Studio & Gemini

Testing tunnel reachability is incomplete without verifying access to specific target services. Users building AI workflows require access to Google AI Studio and the Gemini API.

### Target Endpoints:
1. **Gemini API Core Gateway:**
   - Hostname: `generativelanguage.googleapis.com`
   - Test Method: Unauthenticated HTTP `GET /v1beta/models` over TLS.
   - Expected Response without API key: `HTTP 400 Bad Request` with structured JSON payload (`"API key not valid"`). This definitively proves end-to-end transport, TLS negotiation, and Google API gateway reachability.
   - Expected Response with optional `GEMINI_API_KEY`: `HTTP 200 OK` listing models.
2. **Google AI Studio Web Application:**
   - Hostname: `aistudio.google.com`
   - Test Method: HTTP `GET /` over TLS following redirects.
   - Expected Response: `HTTP 200 OK` or `HTTP 302 Found`.

### Distinguishing Error Classes:
* **Transport Failure:** DNS NXDOMAIN/bogon, TCP timeout, TLS handshake reset (attributed to censorship or routing outage).
* **Geographic / IP Restriction:** HTTP 403 Forbidden with Google regional restriction notice (the VPS IP itself may be in an unsupported territory or flagged by Google Cloud).
* **Application / Auth Failure:** HTTP 400 / 401 / 404 (transport succeeded, but credentials missing/invalid).

---

## 5. Methodology & Measurement Caveats

1. **Never conflate VPS health with client reachability:** A VPS running in Frankfurt with 10Gbps transit to Google has zero bearing on whether an Irancell user in Shiraz can establish a tunnel.
2. **Account for temporal fluctuations:** Iranian filtering shifts dynamically during peak hours (18:00–23:00 local time) and during political/civil events.
3. **ISP Heterogeneity:** Mobile operators (MCI, Irancell) frequently deploy stricter heuristic rate-limiting than fixed-line providers (Shatel, TCI).
