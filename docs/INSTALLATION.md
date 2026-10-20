# Installation & Setup Guide

**TunnelBench** is designed to run seamlessly on Linux, macOS, and WSL environments with Python 3.11+.

---

## 1. Prerequisites

### Local Controller (Workstation / Laptop)
* **Python:** Version 3.11 or newer (`python3 --version`).
* **OpenSSH Client:** Standard OpenSSH client package (`ssh -V`).
* **Operating System:** Linux (Ubuntu 22.04+, Debian 12+, Fedora, Arch), macOS (12+), or Windows with WSL2.

### Remote Foreign VPS (Server-Side)
* Ubuntu 22.04 LTS, 24.04 LTS, or Debian 12.
* Root or sudoer SSH access with SSH public key configured.
* Docker Engine (if running containerized adapter deployments).

---

## 2. Standard Installation

### Recommended: Virtual Environment (venv)
```bash
# Clone the repository
git clone https://github.com/Ariya99/TunnelBench.git
cd TunnelBench

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install package in editable development mode
pip install -e .
```

### With Developer Dependencies (Pytest, Ruff, Mypy)
```bash
pip install -e ".[dev]"
```

---

## 3. Verify Installation

Run the built-in system preflight doctor:
```bash
tunnelbench doctor
```
Expected output:
```text
=== TunnelBench Preflight Doctor ===
[PASS] Python Version: 3.12.x (>= 3.11 required)
[PASS] Operating System: Linux (x86_64)
[PASS] OpenSSH Client: OpenSSH_9.6p1
[PASS] Docker Client: Available
[PASS] Report Storage: ~/.local/share/tunnelbench/reports (Writable)
[PASS] System preflight completed successfully. Ready for benchmarks.
```
