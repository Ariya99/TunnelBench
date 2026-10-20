"""Report Export and Persistence Engine (JSON and CSV).

Outputs hierarchical JSON for programmatic parsing and flattened, row-per-probe
CSV for spreadsheet and statistical analysis.
"""

from __future__ import annotations

import csv
import io
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from tunnelbench.models import ReportModel
from tunnelbench.redaction import redact


CSV_COLUMNS = [
    "run_id",
    "timestamp_utc",
    "tool_version",
    "test_phase",
    "overall_status",
    "vps_profile",
    "isp",
    "connection_type",
    "region",
    "adapter_name",
    "probe_id",
    "probe_name",
    "probe_category",
    "target",
    "probe_status",
    "duration_ms",
    "error_code",
    "error_message",
]


class ReportManager:
    """Manages saving, listing, and exporting TunnelBench reports."""

    def __init__(self, report_dir: Optional[Path] = None) -> None:
        if report_dir is None:
            env_dir = os.environ.get("TUNNELBENCH_REPORT_DIR")
            if env_dir:
                self.report_dir = Path(env_dir)
            else:
                preferred = Path(os.path.expanduser("~/.local/share/tunnelbench/reports"))
                try:
                    preferred.mkdir(parents=True, exist_ok=True, mode=0o700)
                    self.report_dir = preferred
                except OSError:
                    self.report_dir = Path.cwd() / ".tunnelbench" / "reports"
        else:
            self.report_dir = Path(report_dir)

        self._ensure_report_dir()

    def _ensure_report_dir(self) -> None:
        if not self.report_dir.exists():
            self.report_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    def save_report(self, report: ReportModel) -> Tuple[Path, Path]:
        """Saves report as both JSON and CSV files."""
        self._ensure_report_dir()
        clean_dict = redact(report.to_dict())
        # Preserve public test run identifier
        clean_dict["run_id"] = report.run_id

        # 1. Write JSON
        json_path = self.report_dir / f"report_{report.run_id}.json"
        temp_json = json_path.with_suffix(".tmp")
        with open(temp_json, "w", encoding="utf-8") as f:
            json.dump(clean_dict, f, indent=2)
        temp_json.chmod(0o600)
        temp_json.replace(json_path)

        # 2. Write CSV
        csv_path = self.report_dir / f"report_{report.run_id}.csv"
        temp_csv = csv_path.with_suffix(".tmp")
        csv_rows = self.flatten_to_csv_rows(clean_dict)
        with open(temp_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for row in csv_rows:
                writer.writerow(row)
        temp_csv.chmod(0o600)
        temp_csv.replace(csv_path)

        return json_path, csv_path

    @staticmethod
    def flatten_to_csv_rows(report_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Converts report JSON structure into flat rows for CSV analysis."""
        rows: List[Dict[str, Any]] = []
        run_id = report_dict.get("run_id", "")
        ts = report_dict.get("timestamp_utc", "")
        tool_ver = report_dict.get("tool_version", "")
        phase = report_dict.get("test_phase", "")
        status = report_dict.get("status", "")

        vps = report_dict.get("vps_profile") or {}
        vps_name = vps.get("name", "")

        env = report_dict.get("environment") or {}
        isp = env.get("isp", "")
        conn_type = env.get("connection_type", "")
        region = env.get("region", "")

        adapter = report_dict.get("adapter") or {}
        adapter_name = adapter.get("name", "")

        results = report_dict.get("results") or []
        for r in results:
            rows.append(
                {
                    "run_id": run_id,
                    "timestamp_utc": ts,
                    "tool_version": tool_ver,
                    "test_phase": phase,
                    "overall_status": status,
                    "vps_profile": vps_name,
                    "isp": isp,
                    "connection_type": conn_type,
                    "region": region,
                    "adapter_name": adapter_name,
                    "probe_id": r.get("probe_id", ""),
                    "probe_name": r.get("name", ""),
                    "probe_category": r.get("category", ""),
                    "target": r.get("target", ""),
                    "probe_status": r.get("status", ""),
                    "duration_ms": r.get("duration_ms", 0.0),
                    "error_code": r.get("error_code", ""),
                    "error_message": r.get("error_message", ""),
                }
            )
        return rows

    def list_reports(self) -> List[Dict[str, Any]]:
        """Returns metadata for all stored JSON reports."""
        reports: List[Dict[str, Any]] = []
        if not self.report_dir.exists():
            return reports

        for p in sorted(self.report_dir.glob("report_*.json"), reverse=True):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                reports.append(
                    {
                        "run_id": data.get("run_id"),
                        "timestamp_utc": data.get("timestamp_utc"),
                        "test_phase": data.get("test_phase"),
                        "status": data.get("status"),
                        "passed": (data.get("summary") or {}).get("passed", 0),
                        "total": (data.get("summary") or {}).get("total_checks", 0),
                        "path": str(p),
                    }
                )
            except Exception:
                continue
        return reports

    def load_report(self, run_id: str) -> Dict[str, Any]:
        """Loads and returns specific report by run_id."""
        p = self.report_dir / f"report_{run_id}.json"
        if not p.exists():
            # Allow partial run_id search
            matches = list(self.report_dir.glob(f"report_*{run_id}*.json"))
            if matches:
                p = matches[0]
            else:
                raise FileNotFoundError(f"Report for run_id '{run_id}' not found.")

        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
