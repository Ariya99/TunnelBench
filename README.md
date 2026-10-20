# TunnelBench 🛰️

[![CI](https://github.com/Ariya99/TunnelBench/actions/workflows/ci.yml/badge.svg)](https://github.com/Ariya99/TunnelBench/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**TunnelBench** is an open-source, laptop-controlled diagnostic, benchmarking, and decision-support CLI tool designed to evaluate foreign VPS reachability, benchmark VPN and proxy tunnel technologies, validate access network connectivity from restricted environments (such as Iran), and verify reachability to specific AI destinations (notably **Google AI Studio** and the **Gemini API**).

---

## 💡 What TunnelBench Is & Is Not

### What TunnelBench Does:
* **Separates Infrastructure from Reachability:** Distinguishes whether your foreign VPS is healthy from whether an access ISP (e.g., Irancell, MCI, Shatel) allows packets to reach it.
* **Probes Filtering Mechanics:** Characterizes specific censorship mechanisms: DNS bogon injection (`10.10.34.0/24`), TCP connection resets/timeouts, and TLS SNI handshake disruptions.
* **Orchestrates Reviewed Tunnel Adapters:** Deploys and manages tunnel stacks (starting with **Xray-core VLESS-REALITY-Vision**) with strict user approval gates and least-privilege Docker parameters.
* **Validates Target Workloads:** Specifically tests whether target platforms like **Google AI Studio** and **Gemini API** are reachable, distinguishing transport reachability from regional restrictions (`HTTP 403` geo block) and authentication states (`HTTP 400`/`401`).
* **Generates Reproducible Data:** Outputs standardized JSON (`1.0.0`) and row-per-attempt CSV reports for longitudinal analysis.

### What TunnelBench Does NOT Do:
* **Not a Magic Bypass Guarantee:** TunnelBench will not promise that any protocol works unconditionally. Its mission is to measure and tell you what is failing and why.
* **Not an Attack Tool or Port Scanner:** It never scans ranges or performs aggressive probes. All measurements target user-configured destinations.
* **Not a Credential Vault:** It never persists private keys, passwords, or UUIDs in configuration files.

---

## ⚡ The Cardinal Principle of Restricted Network Testing

> ⚠️ **A healthy foreign VPS does not imply a reachable tunnel.**
>
> A VPS in Frankfurt or Helsinki with 10Gbps connectivity and 100% uptime has zero bearing on whether an Irancell subscriber in Tehran or a Shatel user in Tabriz can establish an encrypted tunnel to it.
>
> TunnelBench enforces a strict two-phase separation:
> 1. **Server Baseline Diagnostics:** Read-only verification of remote VPS system resources and foreign internet egress.
> 2. **Client-Side Network Validation:** In-situ measurement from the operator's actual access network.

---

## 📋 Protocol Adapter Status

| Adapter | Status | Implementation State | Default Mode | Description |
| :--- | :--- | :--- | :--- | :--- |
| **`xray-reality`** | `EXPERIMENTAL` | Implemented (v0.1.0) | Docker (Pinned) | VLESS + REALITY + XTLS-Vision. Masquerades as legitimate TLS to decoy domains without self-signed certs. Tested with unit mocks; requires live-network field validation. |
| **`ssh-socks`** | `EXPERIMENTAL` | Implemented (v0.1.0) | Native (OpenSSH) | OpenSSH dynamic application-level SOCKS5 proxy baseline. Tested with unit mocks; requires live-network field validation. |
| **`trojan`** | `PLANNED` | Not Implemented | Docker | Masquerades as HTTPS. Requires dedicated domain and TLS cert. |
| **`shadowsocks-2022`** | `PLANNED` | Not Implemented | Docker | Modern AEAD cipher stack. |
| **`wireguard`** | `PLANNED` | Not Implemented | Docker / Kernel | Planned as a diagnostic contrast probe. |
| **`openvpn`** | `PLANNED` | Not Implemented | Docker | Planned as a diagnostic contrast probe. |

*Definitions:*
- **`PLANNED`**: Researched and specified, but not yet implemented in source code.
- **`EXPERIMENTAL`**: Implemented in source code and unit-tested with mocks, but pending verification on live foreign VPS infrastructure and Iranian access networks.
- **`SUPPORTED`**: Passes all four criteria: full implementation, unit tests, live VPS verification, and field validation on active restricted networks.

---

## 🚀 Quick Start

### 1. Installation

Requires Python 3.11+:

```bash
git clone https://github.com/Ariya99/TunnelBench.git
cd TunnelBench

python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Verify your local environment:
```bash
tunnelbench doctor
```

### 2. Register a Foreign VPS Profile

Add your test VPS (Zero credentials stored; uses your local SSH key or `ssh-agent`):
```bash
tunnelbench vps add \
  --name hetzner-fsn \
  --host 198.51.100.25 \
  --port 22 \
  --user root \
  --key-path ~/.ssh/id_ed25519 \
  --tag germany --tag hetzner
```

List registered profiles:
```bash
tunnelbench vps list
```

### 3. Run Foreign VPS Baseline Diagnostics (Read-Only)

Diagnose remote VPS CPU, RAM, disk capacity, and outbound internet transit:
```bash
tunnelbench baseline run --profile hetzner-fsn
```

### 4. Deploy Reviewed Adapter (`xray-reality`)

Inspect proposed actions, confirm via explicit approval gate, and deploy:
```bash
tunnelbench deploy --profile hetzner-fsn --candidate xray-reality
```
*Note: TunnelBench prints a private client connection link directly to your terminal. It is automatically scrubbed from saved reports and logs.*

### 5. Validate from Local Iranian Network (Client Check)

Run client diagnostics from your local machine to test DNS tampering, TCP reachability, and TLS handshake:
```bash
tunnelbench client-check \
  --profile hetzner-fsn \
  --isp "Irancell" \
  --connection-type "mobile" \
  --region "Tehran" \
  --repeat 3
```

### 6. Validate Target Service (Google AI Studio & Gemini)

Verify reachability to Google AI Studio endpoints through your local proxy:
```bash
tunnelbench target-check --target gemini --proxy socks5://127.0.0.1:10808
```

### 7. Export and Compare Test Runs

List stored benchmark runs:
```bash
tunnelbench report list
```

Compare two runs to identify latency degradation or filtering transitions:
```bash
tunnelbench report compare <run-id-a> <run-id-b>
```

Clean up deployed resources when testing finishes:
```bash
tunnelbench cleanup --profile hetzner-fsn --candidate xray-reality
```

---

## 🔒 Security & Privacy

* **Strict SSH Verification:** Strict host key checking is enforced (`StrictHostKeyChecking=yes`). Host key changes abort execution.
* **Centralized Secret Redaction:** UUIDs, private keys, API keys, URLs, and bearer tokens are automatically redacted across all terminal outputs, exception traces, JSON, and CSV exports.
* **Safe Subprocesses:** Subprocesses use static argument arrays (`argv`), completely preventing shell command injection.
* **Explicit Mutation Approval:** No Docker container, service, or configuration is ever installed or modified without an explicit user approval prompt.

---

## 📚 Documentation Index

* [System Architecture](docs/ARCHITECTURE.md)
* [Iranian Network Testing Guide](docs/IRAN_NETWORK_TESTING.md)
* [Research & Evidence Base](docs/RESEARCH.md)
* [Protocol Adapters Specification](docs/PROTOCOL_ADAPTERS.md)
* [Security Model & Threat Matrix](docs/SECURITY_MODEL.md)
* [Report Schema (JSON & CSV)](docs/REPORT_SCHEMA.md)
* [Installation Guide](docs/INSTALLATION.md)
* [Troubleshooting & Decision Trees](docs/TROUBLESHOOTING.md)
* [Product Roadmap](docs/ROADMAP.md)

---

## 🤝 Contributing

Contributions are warmly welcomed! Please read [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md) before submitting pull requests or vulnerability reports.

---

## 📄 License

TunnelBench is released under the [MIT License](LICENSE).
Copyright (c) 2026 Ariya99 and TunnelBench Contributors.
