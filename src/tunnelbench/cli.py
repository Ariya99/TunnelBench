"""Command Line Interface for TunnelBench.

Discoverable, structured CLI for laptop-controlled foreign VPS diagnostics,
adapter deployments, Iranian client validation, and target-service benchmarking.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from tunnelbench import __version__
from tunnelbench.adapters import get_adapter, list_adapters
from tunnelbench.comparison.comparator import ReportComparator
from tunnelbench.config import ConfigError, ConfigManager
from tunnelbench.diagnostics.baseline import BaselineDiagnostics
from tunnelbench.diagnostics.preflight import PreflightChecker
from tunnelbench.models import CheckStatus
from tunnelbench.redaction import redact
from tunnelbench.reporting.export import ReportManager
from tunnelbench.validation.client_check import ClientNetworkValidator
from tunnelbench.validation.target_check import TargetServiceValidator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tunnelbench",
        description="TunnelBench: Diagnostic & Benchmarking CLI for Restrictive Network Environments",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # doctor
    subparsers.add_parser("doctor", help="Run local system environment preflight checks")

    # vps
    vps_parser = subparsers.add_parser("vps", help="Manage foreign VPS profiles")
    vps_sub = vps_parser.add_subparsers(dest="vps_action", help="VPS operations")

    # vps add
    vps_add = vps_sub.add_parser("add", help="Register a new foreign VPS profile")
    vps_add.add_argument("--name", required=True, help="Unique profile name")
    vps_add.add_argument("--host", required=True, help="VPS IP address or hostname")
    vps_add.add_argument("--port", type=int, default=22, help="SSH port (default: 22)")
    vps_add.add_argument("--user", default="root", help="SSH username (default: root)")
    vps_add.add_argument(
        "--auth-method", choices=["key", "agent"], default="key", help="SSH authentication method"
    )
    vps_add.add_argument("--key-path", help="Path to local SSH private key file")
    vps_add.add_argument("--tag", action="append", dest="tags", help="Optional tags/metadata")

    # vps list
    vps_sub.add_parser("list", help="List registered VPS profiles")

    # vps show
    vps_show = vps_sub.add_parser("show", help="Display details of a VPS profile")
    vps_show.add_argument("name", help="Profile name")

    # vps remove
    vps_rm = vps_sub.add_parser("remove", help="Delete a VPS profile")
    vps_rm.add_argument("name", help="Profile name to remove")

    # baseline
    base_parser = subparsers.add_parser("baseline", help="Run read-only baseline VPS diagnostics")
    base_sub = base_parser.add_subparsers(dest="baseline_action")
    base_run = base_sub.add_parser("run", help="Execute baseline diagnostics on a foreign VPS")
    base_run.add_argument("--profile", required=True, help="Name of VPS profile to test")

    # candidates
    cand_parser = subparsers.add_parser("candidates", help="Inspect tunnel & proxy adapter options")
    cand_sub = cand_parser.add_subparsers(dest="candidates_action")
    cand_sub.add_parser("list", help="List all candidate adapters and maintenance statuses")

    # deploy
    deploy_parser = subparsers.add_parser("deploy", help="Deploy tunnel adapter to foreign VPS")
    deploy_parser.add_argument("--profile", required=True, help="Target VPS profile")
    deploy_parser.add_argument(
        "--candidate", default="xray-reality", help="Adapter to deploy (default: xray-reality)"
    )
    deploy_parser.add_argument(
        "--yes", action="store_true", help="Bypass interactive confirmation gate"
    )

    # client-check
    client_parser = subparsers.add_parser(
        "client-check", help="Run client-side diagnostics from current network"
    )
    client_parser.add_argument("--profile", help="VPS profile to test against")
    client_parser.add_argument("--host", help="Direct target host/IP")
    client_parser.add_argument("--port", type=int, default=443, help="Target port (default: 443)")
    client_parser.add_argument("--sni", default="www.microsoft.com", help="Decoy SNI for TLS probe")
    client_parser.add_argument("--proxy", help="Local proxy URL (e.g., socks5://127.0.0.1:10808)")
    client_parser.add_argument("--isp", default="unspecified", help="Current ISP (e.g. Irancell, MCI, Shatel)")
    client_parser.add_argument(
        "--connection-type", choices=["mobile", "fixed", "unknown"], default="unknown"
    )
    client_parser.add_argument("--region", default="unspecified", help="Approximate region (e.g. Tehran)")
    client_parser.add_argument("--repeat", type=int, default=3, help="Number of TCP probes (default: 3)")

    # target-check
    target_parser = subparsers.add_parser(
        "target-check", help="Validate Google AI Studio and target web reachability"
    )
    target_parser.add_argument(
        "--target",
        choices=["gemini", "https", "all"],
        default="all",
        help="Target destination profile (default: all)",
    )
    target_parser.add_argument("--proxy", help="Proxy URL to route through (e.g., socks5://127.0.0.1:10808)")
    target_parser.add_argument("--key", help="Optional Gemini API key for authenticated test")

    # report
    rep_parser = subparsers.add_parser("report", help="Inspect and compare benchmark reports")
    rep_sub = rep_parser.add_subparsers(dest="report_action")
    rep_sub.add_parser("list", help="List stored test reports")
    rep_show = rep_sub.add_parser("show", help="Display details for a run ID")
    rep_show.add_argument("run_id", help="UUID or prefix of test run")
    rep_comp = rep_sub.add_parser("compare", help="Compare two test runs")
    rep_comp.add_argument("run_a", help="First run ID (baseline)")
    rep_comp.add_argument("run_b", help="Second run ID (candidate)")

    # cleanup
    clean_parser = subparsers.add_parser("cleanup", help="Tear down deployed tunnel resources")
    clean_parser.add_argument("--profile", required=True, help="Target VPS profile")
    clean_parser.add_argument(
        "--candidate", default="xray-reality", help="Adapter to remove (default: xray-reality)"
    )
    clean_parser.add_argument(
        "--yes", action="store_true", help="Bypass interactive confirmation gate"
    )

    return parser


def handle_doctor() -> int:
    """Handles `tunnelbench doctor`."""
    checker = PreflightChecker()
    report = checker.run_all()
    rep_mgr = ReportManager()
    jpath, cpath = rep_mgr.save_report(report)

    print("\n=== TunnelBench Preflight Doctor ===")
    for r in report.results:
        symbol = "[PASS]" if r.status == CheckStatus.PASS else f"[{r.status.value}]"
        print(f"{symbol:<8} {r.name:<32} {r.details or r.error_message}")
    print("-" * 55)
    print(f"Overall Preflight: {report.status.value}")
    print(f"Report saved: {jpath}\n")
    return 0 if report.status == CheckStatus.PASS else 1


def handle_vps(args: argparse.Namespace) -> int:
    """Handles `tunnelbench vps ...`."""
    cfg = ConfigManager()
    action = args.vps_action

    if action == "add":
        try:
            p = cfg.add_profile(
                name=args.name,
                host=args.host,
                port=args.port,
                user=args.user,
                auth_method=args.auth_method,
                key_path=args.key_path,
                tags=args.tags,
            )
            print(f"[OK] VPS profile '{p.name}' registered successfully.")
            return 0
        except ConfigError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            return 1

    elif action == "list":
        profiles = cfg.list_profiles()
        if not profiles:
            print("No VPS profiles registered. Use 'tunnelbench vps add --name <n> --host <h>'.")
            return 0
        print(f"\n{'Name':<16} | {'Target':<28} | {'Auth':<8} | {'Tags'}")
        print("-" * 65)
        for p in profiles:
            target = f"{p.user}@{p.host}:{p.port}"
            tags = ", ".join(p.tags) if p.tags else "none"
            print(f"{p.name:<16} | {target:<28} | {p.auth_method:<8} | {tags}")
        print()
        return 0

    elif action == "show":
        try:
            p = cfg.get_profile(args.name)
            print(json.dumps(redact(p.to_dict()), indent=2))
            return 0
        except ConfigError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            return 1

    elif action == "remove":
        try:
            cfg.remove_profile(args.name)
            print(f"[OK] Profile '{args.name}' removed.")
            return 0
        except ConfigError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            return 1

    print("Please specify a VPS action: add, list, show, remove")
    return 1


def handle_baseline(args: argparse.Namespace) -> int:
    """Handles `tunnelbench baseline run --profile <n>`."""
    cfg = ConfigManager()
    try:
        prof = cfg.get_profile(args.profile)
    except ConfigError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    print(f"\n[INFO] Starting foreign VPS baseline diagnostics for '{prof.name}' ({prof.host})...")
    runner = BaselineDiagnostics(prof)
    report = runner.run_all()
    rep_mgr = ReportManager()
    jpath, cpath = rep_mgr.save_report(report)

    print("\n=== Baseline Diagnostic Results ===")
    for r in report.results:
        symbol = "[PASS]" if r.status == CheckStatus.PASS else f"[{r.status.value}]"
        extra = f"({r.duration_ms:.1f}ms)"
        print(f"{symbol:<8} {r.name:<32} {extra:<10} {r.error_message or ''}")
    print("-" * 60)
    print(f"Overall Status: {report.status.value} (Passed: {report.summary.passed}/{report.summary.total_checks})")
    print(f"Full JSON Report: {jpath}")
    print(f"Tabular CSV:     {cpath}\n")
    return 0 if report.status == CheckStatus.PASS else 1


def handle_candidates(args: argparse.Namespace) -> int:
    """Handles `tunnelbench candidates list`."""
    adapters = list_adapters()
    print("\n=== Evaluated Protocol Adapters ===")
    print(f"{'Adapter Name':<16} | {'Status':<14} | {'Description'}")
    print("-" * 75)
    for a in adapters:
        print(f"{a.name:<16} | {a.status.value:<14} | {a.description}")
    print()
    return 0


def handle_deploy(args: argparse.Namespace) -> int:
    """Handles `tunnelbench deploy --profile <p> --candidate <c>`."""
    cfg = ConfigManager()
    try:
        prof = cfg.get_profile(args.profile)
    except ConfigError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    try:
        adapter = get_adapter(args.candidate)
    except KeyError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    from tunnelbench.remote.ssh import SSHClient

    ssh = SSHClient(prof)

    print(f"\n[INFO] Checking deployment prerequisites for '{adapter.name}'...")
    prereqs = adapter.check_prerequisites(prof, ssh)
    for p in prereqs:
        sym = "[PASS]" if p.status == CheckStatus.PASS else f"[{p.status.value}]"
        print(f"  {sym:<8} {p.name:<30} {p.error_message or ''}")

    if any(p.status == CheckStatus.FAIL for p in prereqs):
        print(f"[ERROR] Prerequisites failed. Aborting deployment.", file=sys.stderr)
        return 1

    plan = adapter.build_deployment_plan(prof)
    if not adapter.require_user_approval(plan, auto_approve=args.yes):
        print("[ABORTED] Deployment cancelled by operator.")
        return 1

    print("\n[INFO] Executing deployment plan on remote VPS...")
    success, probes, client_data = adapter.deploy(prof, plan, ssh)

    print("\n=== Deployment Verification ===")
    for p in probes:
        sym = "[PASS]" if p.status == CheckStatus.PASS else f"[{p.status.value}]"
        print(f"  {sym:<8} {p.name:<30} {p.error_message or ''}")

    if success:
        print("\n" + "=" * 65)
        print(" [SUCCESS] ADAPTER DEPLOYED SUCCESSFULLY")
        print("=" * 65)
        if "client_link" in client_data:
            print("\nOperator Client Link (Keep Private!):")
            print(f"  {client_data['client_link']}")
        print("\nNext Step:")
        print(f"  Test reachability from your client network:")
        print(f"  tunnelbench client-check --profile {prof.name}")
        print("=" * 65 + "\n")
        return 0
    else:
        print(f"\n[ERROR] Deployment verification failed.", file=sys.stderr)
        return 1


def handle_client_check(args: argparse.Namespace) -> int:
    """Handles `tunnelbench client-check ...`."""
    target_host = args.host
    target_port = args.port

    if args.profile:
        cfg = ConfigManager()
        try:
            prof = cfg.get_profile(args.profile)
            target_host = prof.host
        except ConfigError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            return 1

    if not target_host:
        print("[ERROR] Please specify either --profile <name> or --host <ip/hostname>", file=sys.stderr)
        return 1

    print(f"\n[INFO] Running client-side reachability diagnostics for {target_host}:{target_port}...")
    print(f"  ISP: {args.isp} | Type: {args.connection_type} | Region: {args.region}")

    validator = ClientNetworkValidator(
        target_host=target_host,
        target_port=target_port,
        sni=args.sni,
        proxy_url=args.proxy,
        isp=args.isp,
        connection_type=args.connection_type,
        region=args.region,
    )

    report = validator.run_all(repeat=args.repeat)
    rep_mgr = ReportManager()
    jpath, cpath = rep_mgr.save_report(report)

    print("\n=== Client Network Diagnostic Probes ===")
    for r in report.results:
        sym = "[PASS]" if r.status == CheckStatus.PASS else f"[{r.status.value}]"
        print(f"{sym:<8} {r.name:<32} {r.duration_ms:6.1f}ms  {r.error_message or ''}")
    print("-" * 65)
    print(f"Overall Client Status: {report.status.value}")
    print(f"Full JSON Report: {jpath}")
    print(f"Tabular CSV:     {cpath}\n")
    return 0 if report.status == CheckStatus.PASS else 1


def handle_target_check(args: argparse.Namespace) -> int:
    """Handles `tunnelbench target-check ...`."""
    print(f"\n[INFO] Validating target services (Target: {args.target})...")
    validator = TargetServiceValidator(
        proxy_url=args.proxy,
        gemini_api_key=args.key,
    )
    report = validator.run_all(target=args.target)
    rep_mgr = ReportManager()
    jpath, cpath = rep_mgr.save_report(report)

    print("\n=== Target Service Verification ===")
    for r in report.results:
        sym = "[PASS]" if r.status == CheckStatus.PASS else f"[{r.status.value}]"
        details_str = json.dumps(r.details) if r.details else ""
        print(f"{sym:<8} {r.name:<36} {r.duration_ms:6.1f}ms  {r.error_message or details_str}")
    print("-" * 65)
    print(f"Target Check Status: {report.status.value}")
    print(f"Full JSON Report: {jpath}\n")
    return 0 if report.status == CheckStatus.PASS else 1


def handle_report(args: argparse.Namespace) -> int:
    """Handles `tunnelbench report ...`."""
    rep_mgr = ReportManager()
    action = args.report_action

    if action == "list":
        reports = rep_mgr.list_reports()
        if not reports:
            print("No test reports found.")
            return 0
        print(f"\n{'Run ID':<36} | {'Timestamp':<20} | {'Phase':<14} | {'Status':<6} | {'Passed'}")
        print("-" * 90)
        for r in reports:
            print(
                f"{r['run_id']:<36} | {r['timestamp_utc'][:19]:<20} | {r['test_phase']:<14} | "
                f"{r['status']:<6} | {r['passed']}/{r['total']}"
            )
        print()
        return 0

    elif action == "show":
        try:
            data = rep_mgr.load_report(args.run_id)
            print(json.dumps(data, indent=2))
            return 0
        except FileNotFoundError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            return 1

    elif action == "compare":
        try:
            ra = rep_mgr.load_report(args.run_a)
            rb = rep_mgr.load_report(args.run_b)
            diff = ReportComparator.compare(ra, rb)
            print("\n" + ReportComparator.format_text_summary(diff) + "\n")
            return 0
        except FileNotFoundError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            return 1

    print("Please specify a report action: list, show, compare")
    return 1


def handle_cleanup(args: argparse.Namespace) -> int:
    """Handles `tunnelbench cleanup --profile <p> --candidate <c>`."""
    cfg = ConfigManager()
    try:
        prof = cfg.get_profile(args.profile)
    except ConfigError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    try:
        adapter = get_adapter(args.candidate)
    except KeyError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    if not args.yes:
        confirm = input(
            f"Are you sure you want to clean up '{adapter.name}' on {prof.host}? [y/N]: "
        )
        if confirm.strip().lower() not in ("y", "yes"):
            print("[ABORTED] Cleanup cancelled.")
            return 1

    from tunnelbench.remote.ssh import SSHClient

    ssh = SSHClient(prof)
    print(f"\n[INFO] Executing cleanup for '{adapter.name}' on {prof.host}...")
    success, probes = adapter.cleanup(prof, ssh)
    for p in probes:
        sym = "[PASS]" if p.status == CheckStatus.PASS else f"[{p.status.value}]"
        print(f"  {sym:<8} {p.name:<30} {p.error_message or ''}")
    print("[OK] Cleanup completed.\n")
    return 0 if success else 1


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help()
        return 0

    if args.subcommand == "doctor":
        return handle_doctor()
    elif args.subcommand == "vps":
        return handle_vps(args)
    elif args.subcommand == "baseline":
        return handle_baseline(args)
    elif args.subcommand == "candidates":
        return handle_candidates(args)
    elif args.subcommand == "deploy":
        return handle_deploy(args)
    elif args.subcommand == "client-check":
        return handle_client_check(args)
    elif args.subcommand == "target-check":
        return handle_target_check(args)
    elif args.subcommand == "report":
        return handle_report(args)
    elif args.subcommand == "cleanup":
        return handle_cleanup(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
