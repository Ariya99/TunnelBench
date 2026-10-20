# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-20

### Added
- Complete CLI diagnostic framework with subcommands (`doctor`, `vps`, `baseline`, `candidates`, `deploy`, `client-check`, `target-check`, `report`, `cleanup`).
- Zero-secret foreign VPS profile management system.
- Read-only foreign VPS baseline diagnostic suite.
- Centralized `RedactionEngine` masking UUIDs, keys, tokens, and URIs.
- Reviewed protocol adapter for Xray-core (VLESS + REALITY + XTLS-Vision) container deployment.
- Fallback diagnostic adapter for SSH dynamic SOCKS5 forwarding.
- 7-stage Iranian client-side network validation workflow.
- Target service checker for Google AI Studio and Gemini API.
- Versioned JSON (`1.0.0`) and row-per-attempt CSV reporting.
- Run comparison tool analyzing metric shifts across test runs.
- Full test suite with mocked SSH sessions, unit tests, and CI workflow.
