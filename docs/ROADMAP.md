# TunnelBench Product Roadmap

## Milestone 1: MVP Release (v0.1.0) - Current
- [x] Laptop-controlled command-line interface with subcommands.
- [x] Environment preflight doctor checking local system, SSH, and Docker.
- [x] VPS profile manager with strict zero-secret storage.
- [x] Read-only foreign VPS baseline diagnostics.
- [x] Strict SSH host-key verification policy.
- [x] Centralized secret redaction for UUIDs, keys, URLs, and tokens.
- [x] First fully-reviewed adapter: Xray-core (VLESS + REALITY + XTLS-Vision) containerized deployment.
- [x] Second fallback adapter: SSH Dynamic SOCKS5 diagnostic proxy.
- [x] 7-phase Iranian client-side network validation workflow.
- [x] Target-service validation for Google AI Studio / Gemini API.
- [x] Versioned JSON (`1.0.0`) and granular row-per-attempt CSV reporting.
- [x] Run comparator analyzing latency and error shifts across runs.
- [x] Automated test suite with 100% mocked offline testing.
- [x] GitHub Actions CI workflow.

## Milestone 2: Multi-Protocol Expansion (v0.2.0)
- [ ] Add Trojan-Go / Sing-box adapter with automated certificate staging.
- [ ] Add Shadowsocks 2022 adapter with AEAD multi-user key generation.
- [ ] Add WireGuard contrast probe with handshake drop detection metrics.
- [ ] Implement DNS-over-HTTPS (DoH) client resolution benchmarks (Cloudflare vs Quad9 vs Google).

## Milestone 3: Longitudinal Stability & Matrix Comparison (v0.3.0)
- [ ] Automated continuous stability runner (running periodic probes over 1–24 hours).
- [ ] Matrix comparison dashboard: Compare 5 foreign VPS providers across 3 Iranian ISPs simultaneously.
- [ ] Packet loss estimation via TCP sequence analysis.
- [ ] Automated SNI decoy discovery tool testing which domains handshake cleanest on a given ISP.
