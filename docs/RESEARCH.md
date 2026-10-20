# TunnelBench Research & Evidence Base

**Document Status:** Technical Research & Measurement Hypothesis Base  
**Last Updated:** October 2026  
**Authors:** Ariya99 & TunnelBench Measurement Engineering Team  

---

## 1. Executive Summary

Network measurement in restrictive jurisdictions cannot treat internet access as a binary connected/disconnected state. In Iran, connectivity is subject to centralized policy enforcement coordinated through the Telecommunication Infrastructure Company (TIC / شرکت ارتباطات زیرساخت) and executed across retail ISPs (e.g., Mobile: Irancell, MCI, Rightel; Fixed-line: Shatel, Mokhaberat/TCI, Asiatech, Pars Online, Zitel).

TunnelBench bridges the gap between server-side infrastructure readiness and client-side reachability by establishing reproducible, hypothesis-driven measurement protocols.

---

## 2. Documented Filtering Mechanics & Test Hypotheses

### 2.1 DNS Manipulation & Tampering
* **Mechanism:** DNS requests sent to foreign resolvers (e.g., `8.8.8.8`, `1.1.1.1`) over plain UDP port 53 are frequently intercepted, redirected, or poisoned by network filtering middleboxes.
* **Empirical Evidence (OONI Data 2024–2025):** Web Connectivity telemetry collected across Iranian ASNs documents DNS injection returning private, local IPv4 "bogon" addresses, predominantly within the `10.10.34.0/24` subnet (most frequently `10.10.34.35`), as well as loopback `127.0.0.1` responses.
* **Measurement Approach:** Testing tools cannot trust OS-default DNS resolvers for remote endpoints. TunnelBench evaluates DNS via direct socket resolution, compares against known bogon patterns (`10.10.34.0/24`, `127.0.0.0/8`, `0.0.0.0/8`), and records whether resolution was manipulated or clean.

### 2.2 TCP Resets and Connection Timeouts
* **Mechanism:** Deep Packet Inspection (DPI) equipment deployed at transit gateways and major ISP exchanges inspects TCP handshakes. If a destination IP is restricted or flagged, SYN packets may be silently dropped (inducing connection timeout) or an injected TCP RST packet may be returned.
* **Field Observation:** Outbound TCP connect latency (`SYN` -> `SYN-ACK`) diverges drastically between domestic endpoints (< 25ms) and foreign VPS endpoints (often > 120ms or dropping into 10–30s timeout windows). Injected TCP RSTs often arrive in < 30ms with anomalous TTL values.
* **Hypothesis to Test:** Whether destination IP/port blocking is bidirectional, whether RST injection occurs before or after the SYN-ACK, and whether non-standard ports (e.g., 8443, 2053) exhibit different drop rates than standard ports (443, 80).

### 2.3 TLS SNI Filtering & Handshake Disruption
* **Mechanism:** Plaintext Server Name Indication (SNI) in the TLS `ClientHello` is parsed by DPI middleboxes. If the SNI matches a blocked domain pattern, the handshake is aborted via injected RSTs or dropped packets.
* **Active Probing Reports:** Research literature (e.g., Censored Planet, citizen lab reports) documents active probing systems. When a foreign server accepts TLS handshakes mimicking popular services without completing expected certificate handshakes or when traffic anomalies appear, the foreign IP address may be throttled or graylisted.
* **Hypothesis to Test:** Whether connection failure occurs at TCP connect time (IP/port block) or strictly during TLS ClientHello transmission (SNI-based DPI trigger).

### 2.4 WireGuard and UDP Protocol Throttling
* **Upstream Status:** WireGuard is actively maintained upstream in the Linux kernel and user space.
* **Protocol Characteristics:** Standard WireGuard uses a fixed, identifiable packet header structure (the initial handshake initiation packet begins with fixed message type `0x01` followed by a 3-byte sender index).
* **Research Hypothesis & Reported Observations:** Public digital rights telemetry (OONI, Censored Planet) and circumvention research report that Iranian mobile operators frequently drop or throttle unmasked WireGuard handshake UDP packets within seconds.
* **Qualification:** WireGuard drop behavior is an empirical hypothesis to measure, not a guaranteed universal state across every Iranian network or enterprise line. TunnelBench treats standard WireGuard as a contrast probe rather than assuming it is unconditionally blocked everywhere.

### 2.5 VLESS with REALITY and XTLS-Vision
* **Upstream Status:** Actively developed by the open-source XTLS community (Project X / Xray-core).
* **Mechanism:** REALITY circumvents TLS-in-TLS identification by acting as a transparent TLS reverse-proxy to a legitimate foreign server (decoy SNI, such as public CDN or cloud domains). The client sends a TLS `ClientHello` matching the decoy's cipher suites and SNI, while incorporating a short authentication key. If authentication succeeds, Xray intercepts the stream; if an unauthorized active prober probes the server, the connection is passed directly to the genuine decoy server.
* **Field Status & Limitations:** While widely adopted in circumvention tooling, VLESS-REALITY is **not a guaranteed bypass**. Its success depends heavily on:
  1. The specific decoy SNI chosen (if the decoy domain is already filtered in Iran, the handshake fails).
  2. The reputation and ASN of the foreign VPS IP.
  3. Traffic volume heuristics and active probing heuristics applied by specific Iranian ISPs.
* **TunnelBench Release Status:** Labeled **EXPERIMENTAL** in TunnelBench v0.1.0 until verified on live foreign VPS infrastructure and Iranian client connections.

---

## 3. Protocol Candidate Matrix

| Candidate | Upstream Maintenance Status | Linux VPS Support | Censorship Resistance Hypothesis | TunnelBench Status | Verification State |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Xray VLESS-REALITY (Vision)** | Active (XTLS Community) | Excellent | High (Decoy TLS impersonation) | **EXPERIMENTAL** | Implemented, unit-tested with mocks; pending live VPS and field verification. |
| **SSH Dynamic SOCKS5** | Active (OpenSSH) | Native | Low (Easily fingerprinted on high throughput) | **EXPERIMENTAL** | Implemented, unit-tested with mocks; pending live VPS verification. |
| **Trojan / Trojan-Go** | Maintained / Varied | Good | Medium (Requires dedicated domain + valid TLS cert) | **PLANNED** | Not yet implemented in v0.1.0. |
| **Shadowsocks 2022** | Maintained (AEAD spec) | Excellent | Medium-Low (Susceptible to UDP drop / port block) | **PLANNED** | Not yet implemented in v0.1.0. |
| **Standard WireGuard** | Active (Kernel upstream) | Native | Low (Handshake header signature flagged by DPI) | **PLANNED** | Contrast probe only; not yet implemented. |
| **OpenVPN (TCP/UDP)** | Active (OpenVPN project) | High | Low (Static TLS handshake signatures matched by DPI) | **PLANNED** | Contrast probe only; not yet implemented. |

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
* **Transport Failure:** DNS NXDOMAIN/bogon, TCP timeout, TLS handshake reset (attributed to domestic censorship or routing outage).
* **Explicit Geographic / IP Restriction:** HTTP 403 Forbidden specifically returning `"User location is not supported"` in response body (indicating Google Cloud does not service the VPS egress IP location).
* **Policy / Auth Failure:** HTTP 403 Forbidden without location restriction (indicating account policy, API restrictions, or missing credentials).
* **Application / Transport Success:** HTTP 400 with invalid API key notice (transport is operational).

---

## 5. Methodology & Measurement Caveats

1. **Never conflate VPS health with client reachability:** A foreign VPS in Frankfurt with 10Gbps transit to Google has zero bearing on whether an Irancell subscriber in Tehran can establish an encrypted tunnel to it.
2. **Account for temporal fluctuations:** Iranian filtering shifts dynamically during peak hours (18:00–23:00 local time) and during political/civil events.
3. **ISP Heterogeneity:** Mobile operators (MCI, Irancell) frequently deploy stricter heuristic rate-limiting than fixed-line providers (Shatel, TCI).
4. **Evidence Grounding:** All conclusions regarding censorship must be grounded in measurable packet and handshake events rather than assumptions.
