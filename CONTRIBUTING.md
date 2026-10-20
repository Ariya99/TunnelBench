# Contributing to TunnelBench

Thank you for your interest in contributing to TunnelBench! We welcome contributions from network measurement researchers, systems architects, and software engineers.

---

## 1. Development Principles

1. **Security First:** Never weaken SSH host key checking, never store plaintext secrets, and maintain 100% test coverage for credential redaction.
2. **Measurement Integrity:** Never classify an ambiguous timeout as intentional censorship unless verified by empirical packet/handshake evidence.
3. **Reproducibility:** Every test phase must produce verifiable, machine-readable JSON and CSV outputs.
4. **Offline Testability:** All automated unit and integration tests must run without requiring live foreign VPS credentials or active network access.

---

## 2. Setting Up Development Environment

```bash
git clone https://github.com/Ariya99/TunnelBench.git
cd TunnelBench
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run tests and linters:
```bash
pytest
ruff check .
mypy src/
```

---

## 3. Pull Request Guidelines

- Branch names should be descriptive (e.g., `feat/shadowsocks-adapter`, `fix/redaction-regex`).
- Ensure all tests pass.
- Write unit tests for all new modules and bug fixes.
- Document any schema changes in `docs/REPORT_SCHEMA.md`.
