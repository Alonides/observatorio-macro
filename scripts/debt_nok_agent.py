#!/usr/bin/env python3
"""Scheduled operational agent for the Debt/NOK monitor.

The daily macro store intentionally retains a compact history for the public
panel.  The NOK residual needs a longer common sample after aligning Norwegian,
Swedish, oil and volatility calendars.  This agent therefore maintains a
separate, official factor cache from 2018 onward and never lowers the frozen
walk-forward calibration merely to fit the compact store.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from observatorio.debt_nok_v04.history import fetch_historical_series  # noqa: E402
from observatorio.debt_nok_v04.residual import build_nok_residual  # noqa: E402
from observatorio.debt_nok_v1.report import build_report  # noqa: E402

DATA_DIR = ROOT / "data"
MONITOR_DIR = DATA_DIR / "debt_nok"
FACTOR_START = "2018-01-01"
FACTOR_LIMIT = 2600
FACTOR_IDS = (
    "DEXNOUS",
    "DEXUSEU",
    "DEXSDUS",
    "DCOILBRENTEU",
    "VIXCLS",
)


def _load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _atomic_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _merge_points(*groups: list[dict], limit: int = FACTOR_LIMIT) -> list[dict]:
    by_day: dict[str, dict] = {}
    for group in groups:
        for point in group or []:
            if not isinstance(point, dict) or point.get("date") is None or point.get("value") is None:
                continue
            try:
                value = float(point["value"])
            except (TypeError, ValueError):
                continue
            day = str(point["date"])
            by_day[day] = {"date": day, "value": value}
    return [by_day[day] for day in sorted(by_day)][-limit:]


def _exact_product(left: list[dict], right: list[dict]) -> list[dict]:
    left_map = {str(point["date"]): float(point["value"]) for point in left if point.get("date") and point.get("value") is not None}
    right_map = {str(point["date"]): float(point["value"]) for point in right if point.get("date") and point.get("value") is not None}
    return [
        {"date": day, "value": left_map[day] * right_map[day]}
        for day in sorted(left_map.keys() & right_map.keys())
    ]


def _exact_ratio(numerator: list[dict], denominator: list[dict]) -> list[dict]:
    num_map = {str(point["date"]): float(point["value"]) for point in numerator if point.get("date") and point.get("value") is not None}
    den_map = {str(point["date"]): float(point["value"]) for point in denominator if point.get("date") and point.get("value") not in {None, 0}}
    return [
        {"date": day, "value": num_map[day] / den_map[day]}
        for day in sorted(num_map.keys() & den_map.keys())
    ]


def _factor_history(
    compact_series: dict[str, list[dict]],
    cached_series: dict[str, list[dict]],
    no_network: bool,
) -> tuple[dict[str, list[dict]], dict[str, str]]:
    """Return long factor histories, preserving valid cache on source failure."""
    output = dict(compact_series)
    errors: dict[str, str] = {}
    for series_id in FACTOR_IDS:
        fetched: list[dict] = []
        if not no_network:
            try:
                fetched = fetch_historical_series(series_id, start=FACTOR_START)
                if not fetched:
                    raise RuntimeError("official source returned no observations")
            except Exception as exc:  # isolation by factor; cached data remains usable
                errors[series_id] = str(exc)
        merged = _merge_points(
            cached_series.get(series_id, []),
            compact_series.get(series_id, []),
            fetched,
            limit=FACTOR_LIMIT,
        )
        if merged:
            output[series_id] = merged
        elif series_id not in errors:
            errors[series_id] = "no cached or current observations available"
    return output, errors


def _github_output(key: str, value: str) -> None:
    path = os.getenv("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"{key}={value}\n")


def _fingerprint(report: dict) -> str:
    current = report.get("current", {})
    operational = current.get("operational", {}) if isinstance(current, dict) else {}
    blocks = operational.get("blocks", {}) if isinstance(operational, dict) else {}
    states = [str(blocks.get(key, {}).get("state", "missing")) for key in ("URP", "URR", "DSS", "NKS", "NRS")]
    return "|".join([str(report.get("alert", {}).get("level", "unknown")), *states])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("daily", "weekly"), default="daily")
    parser.add_argument("--no-network", action="store_true", help="Use only compact and previously cached factor histories")
    args = parser.parse_args()

    source = _load(DATA_DIR / "series.json", {})
    compact_series = source.get("series")
    if not isinstance(compact_series, dict):
        raise SystemExit("data/series.json does not contain a series object")

    prior_history = _load(MONITOR_DIR / "history.json", {"series": {}}).get("series", {})
    cached_series = prior_history if isinstance(prior_history, dict) else {}
    series, factor_errors = _factor_history(compact_series, cached_series, args.no_network)

    residual = build_nok_residual(series)
    residual_points = residual.get("points", [])
    if residual_points:
        series["NOK_RESIDUAL_Z20"] = residual_points

    report = build_report(series, mode=args.mode)
    report["source_status"] = {
        "factor_start": FACTOR_START,
        "factor_observations": {series_id: len(series.get(series_id, [])) for series_id in FACTOR_IDS},
        "factor_errors": factor_errors,
        "residual_points": len(residual_points),
        "residual_start": residual.get("coverage", {}).get("start"),
        "residual_end": residual.get("coverage", {}).get("end"),
    }

    previous_state = _load(MONITOR_DIR / "state.json", {})
    fingerprint = _fingerprint(report)
    material = bool(report.get("alert", {}).get("material"))
    changed = fingerprint != previous_state.get("fingerprint")
    notify = args.mode == "weekly" or (material and changed)
    report["notification"] = {
        "notify": notify,
        "changed": changed,
        "fingerprint": fingerprint,
        "previous_fingerprint": previous_state.get("fingerprint"),
        "channel": "github_issue_notification",
    }

    eurnok = _exact_product(series.get("DEXNOUS", []), series.get("DEXUSEU", []))
    noksek = _exact_ratio(series.get("DEXNOUS", []), series.get("DEXSDUS", []))
    history_payload = {
        "schema_version": 2,
        "generated_at": report["generated_at"],
        "factor_start": FACTOR_START,
        "series": {
            **{series_id: series.get(series_id, [])[-FACTOR_LIMIT:] for series_id in FACTOR_IDS},
            "EURNOK": eurnok[-FACTOR_LIMIT:],
            "NOKSEK": noksek[-FACTOR_LIMIT:],
            "NOK_RESIDUAL_Z20": residual_points[-FACTOR_LIMIT:],
        },
    }

    _atomic_json(MONITOR_DIR / "latest.json", {key: value for key, value in report.items() if key != "markdown"})
    _atomic_text(MONITOR_DIR / "latest.md", report["markdown"])
    _atomic_json(MONITOR_DIR / "history.json", history_payload)
    _atomic_json(MONITOR_DIR / "state.json", {
        "updated_at": report["generated_at"],
        "asof": report.get("asof"),
        "level": report.get("alert", {}).get("level"),
        "fingerprint": fingerprint,
    })
    if args.mode == "weekly" or notify:
        stamp = report.get("asof") or datetime.now(timezone.utc).date().isoformat()
        _atomic_text(MONITOR_DIR / "reports" / f"{stamp}.md", report["markdown"])

    _github_output("notify", "true" if notify else "false")
    _github_output("mode", args.mode)
    _github_output("level", str(report.get("alert", {}).get("level", "unknown")))
    _github_output("title", str(report.get("notification_title", "Debt/NOK report")).replace("\n", " "))
    _github_output("asof", str(report.get("asof") or "unknown"))

    print(
        f"Debt/NOK {report['model_version']} · {report.get('asof')} · "
        f"{report['alert']['level']} · residual={len(residual_points)} · notify={notify}"
    )
    for series_id, error in sorted(factor_errors.items()):
        print(f"{series_id} warning: {error}", file=sys.stderr)
    if not residual_points:
        print("NOK residual unavailable: operational coverage remains partial", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
