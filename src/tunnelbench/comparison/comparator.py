"""Run Comparator for Benchmarking and Metric Drift Analysis.

Identifies latency deltas, error transitions, and reliability shifts between test runs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ReportComparator:
    """Compares two TunnelBench test runs and quantifies differences."""

    @staticmethod
    def compare(report_a: Dict[str, Any], report_b: Dict[str, Any]) -> Dict[str, Any]:
        """Performs structured comparison between report_a (baseline) and report_b (candidate)."""
        run_a_id = report_a.get("run_id", "A")
        run_b_id = report_b.get("run_id", "B")

        phase_a = report_a.get("test_phase")
        phase_b = report_b.get("test_phase")

        env_a = report_a.get("environment") or {}
        env_b = report_b.get("environment") or {}

        # Flag non-equivalent testing conditions
        is_equivalent_environment = (
            env_a.get("isp") == env_b.get("isp")
            and env_a.get("connection_type") == env_b.get("connection_type")
            and phase_a == phase_b
        )

        sum_a = report_a.get("summary") or {}
        sum_b = report_b.get("summary") or {}

        status_transition = f"{report_a.get('status')} -> {report_b.get('status')}"
        duration_delta_sec = round(
            sum_b.get("duration_seconds", 0.0) - sum_a.get("duration_seconds", 0.0), 2
        )

        # Map probes by probe_id
        probes_a = {p.get("probe_id"): p for p in report_a.get("results", [])}
        probes_b = {p.get("probe_id"): p for p in report_b.get("results", [])}

        all_probe_ids = sorted(set(probes_a.keys()) | set(probes_b.keys()))
        probe_deltas: List[Dict[str, Any]] = []

        for pid in all_probe_ids:
            pa = probes_a.get(pid)
            pb = probes_b.get(pid)

            if pa and pb:
                dur_a = pa.get("duration_ms", 0.0)
                dur_b = pb.get("duration_ms", 0.0)
                delta_ms = round(dur_b - dur_a, 2)
                probe_deltas.append(
                    {
                        "probe_id": pid,
                        "name": pb.get("name", pa.get("name")),
                        "status_a": pa.get("status"),
                        "status_b": pb.get("status"),
                        "status_changed": pa.get("status") != pb.get("status"),
                        "duration_a_ms": dur_a,
                        "duration_b_ms": dur_b,
                        "latency_delta_ms": delta_ms,
                        "error_a": pa.get("error_code"),
                        "error_b": pb.get("error_code"),
                    }
                )
            elif pb and not pa:
                probe_deltas.append(
                    {
                        "probe_id": pid,
                        "name": pb.get("name"),
                        "status_a": "NOT_PRESENT",
                        "status_b": pb.get("status"),
                        "status_changed": True,
                        "duration_a_ms": 0.0,
                        "duration_b_ms": pb.get("duration_ms", 0.0),
                        "latency_delta_ms": 0.0,
                        "error_a": "",
                        "error_b": pb.get("error_code"),
                    }
                )
            elif pa and not pb:
                probe_deltas.append(
                    {
                        "probe_id": pid,
                        "name": pa.get("name"),
                        "status_a": pa.get("status"),
                        "status_b": "NOT_PRESENT",
                        "status_changed": True,
                        "duration_a_ms": pa.get("duration_ms", 0.0),
                        "duration_b_ms": 0.0,
                        "latency_delta_ms": 0.0,
                        "error_a": pa.get("error_code"),
                        "error_b": "",
                    }
                )

        return {
            "run_a": run_a_id,
            "run_b": run_b_id,
            "phase": phase_b,
            "equivalent_conditions": is_equivalent_environment,
            "status_transition": status_transition,
            "duration_delta_seconds": duration_delta_sec,
            "passed_delta": sum_b.get("passed", 0) - sum_a.get("passed", 0),
            "failed_delta": sum_b.get("failed", 0) - sum_a.get("failed", 0),
            "probe_deltas": probe_deltas,
        }

    @staticmethod
    def format_text_summary(diff: Dict[str, Any]) -> str:
        """Renders comparison as readable ASCII table."""
        lines = [
            f"=== Run Comparison: {diff['run_a'][:8]}... vs {diff['run_b'][:8]}... ===",
            f"Overall Status:        {diff['status_transition']}",
            f"Equivalent Context:    {'YES' if diff['equivalent_conditions'] else 'NO (Results may not be directly comparable)'}",
            f"Pass Delta:            {'+' if diff['passed_delta'] >= 0 else ''}{diff['passed_delta']}",
            f"Fail Delta:            {'+' if diff['failed_delta'] >= 0 else ''}{diff['failed_delta']}",
            "",
            f"{'Probe ID':<26} | {'Status A':<8} -> {'Status B':<8} | {'Latency Delta':<14}",
            "-" * 65,
        ]

        for p in diff["probe_deltas"]:
            delta_str = f"{'+' if p['latency_delta_ms'] >= 0 else ''}{p['latency_delta_ms']}ms"
            lines.append(
                f"{p['probe_id']:<26} | {p['status_a']:<8} -> {p['status_b']:<8} | {delta_str:<14}"
            )

        return "\n".join(lines)
