#!/usr/bin/env python3
"""Scheduled operational agent for the Debt/NOK monitor.

The authoritative lane uses only the validated official histories. A separate
v1.0.3 fast lane may extend slow series for a few sessions with overlap-tested
official proxies. Provisional data never overwrite official observations and
can only request human review; they never silently replace the official state.
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
from observatorio.debt_nok_v1.fast_bridge import (  # noqa: E402
    build_fast_lane_payload,
    build_fast_series,
    fetch_fast_proxies,
)
from observatorio.debt_nok_v1.monitor import evaluate_operational  # noqa: E402
from observatorio.debt_nok_v1.report import build_report, render_markdown  # noqa: E402

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
    """Return long official factor histories, preserving valid cache on failure."""
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
    fast = report.get("fast_lane") if isinstance(report.get("fast_lane"), dict) else {}
    fast_fingerprint = str(fast.get("fingerprint") or "fast-unavailable")
    return "|".join([str(report.get("alert", {}).get("level", "unknown")), *states, fast_fingerprint])


def _build_fast_lane(
    official_series: dict[str, list[dict]],
    official_result: dict,
    no_network: bool,
) -> tuple[dict, dict]:
    if no_network:
        proxies: dict[str, list[dict]] = {}
        sources: dict = {}
        errors = {"NETWORK": "network disabled by command-line option"}
    else:
        proxies, sources, errors = fetch_fast_proxies()

    provisional_series, bridge = build_fast_series(
        official_series,
        proxies=proxies,
        sources=sources,
        errors=errors,
    )
    provisional_residual = build_nok_residual(provisional_series)
    provisional_residual_points = provisional_residual.get("points", [])
    if provisional_residual_points:
        provisional_series["NOK_RESIDUAL_Z20"] = provisional_residual_points
    provisional_result = evaluate_operational(provisional_series)
    payload = build_fast_lane_payload(official_result, provisional_result, bridge)
    payload["residual"] = {
        "points": len(provisional_residual_points),
        "start": provisional_residual.get("coverage", {}).get("start"),
        "end": provisional_residual.get("coverage", {}).get("end"),
    }
    return payload, provisional_series


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("daily", "weekly"), default="daily")
    parser.add_argument("--no-network", action="store_true", help="Use only compact and previously cached official histories")
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

    # Authoritative report first. The provisional lane is attached afterwards
    # and cannot modify the official alert, headline or historical series.
    report = build_report(series, mode=args.mode)
    fast_lane, _ = _build_fast_lane(series, report["current"], args.no_network)
    report["fast_lane"] = fast_lane
    report["source_status"] = {
        "factor_start": FACTOR_START,
        "factor_observations": {series_id: len(series.get(series_id, [])) for series_id in FACTOR_IDS},
        "factor_errors": factor_errors,
        "official_residual_points": len(residual_points),
        "official_residual_start": residual.get("coverage", {}).get("start"),
        "official_residual_end": residual.get("coverage", {}).get("end"),
        "fast_bridge_status": fast_lane.get("bridge", {}).get("status"),
        "fast_bridge_active_targets": fast_lane.get("bridge", {}).get("active_targets", []),
        "fast_bridge_errors": fast_lane.get("bridge", {}).get("errors", {}),
        "fast_residual_points": fast_lane.get("residual", {}).get("points", 0),
        "fast_residual_start": fast_lane.get("residual", {}).get("start"),
        "fast_residual_end": fast_lane.get("residual", {}).get("end"),
    }
    report["markdown"] = render_markdown(report)
    if fast_lane.get("review_required"):
        report["notification_title"] = f"Debt/NOK · Señal provisional · {report['report_date']}"

    previous_state = _load(MONITOR_DIR / "state.json", {})
    fingerprint = _fingerprint(report)
    official_material = bool(report.get("alert", {}).get("material"))
    provisional_review = bool(fast_lane.get("review_required"))
    material = official_material or provisional_review
    changed = fingerprint != previous_state.get("fingerprint")
    notify = args.mode == "weekly" or (material and changed)
    report["notification"] = {
        "notify": notify,
        "changed": changed,
        "fingerprint": fingerprint,
        "previous_fingerprint": previous_state.get("fingerprint"),
        "official_material": official_material,
        "provisional_review": provisional_review,
        "channel": "github_issue_notification",
    }

    # Persist only authoritative histories. Proxy points and bridge-generated
    # values remain ephemeral and are represented solely by audit metadata.
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
        "report_date": report.get("report_date"),
        "asof": report.get("asof"),
        "block_asof": report.get("block_asof", {}),
        "freshness": report.get("freshness", {}),
        "level": report.get("alert", {}).get("level"),
        "fast_lane": {
            "status": fast_lane.get("status"),
            "level": fast_lane.get("level"),
            "raw_level": fast_lane.get("raw_provisional_level"),
            "review_required": provisional_review,
            "active_targets": fast_lane.get("bridge", {}).get("active_targets", []),
        },
        "fingerprint": fingerprint,
    })
    if args.mode == "weekly" or notify:
        stamp = report.get("report_date") or datetime.now(timezone.utc).date().isoformat()
        _atomic_text(MONITOR_DIR / "reports" / f"{stamp}.md", report["markdown"])

    _github_output("notify", "true" if notify else "false")
    _github_output("mode", args.mode)
    _github_output("level", str(report.get("alert", {}).get("level", "unknown")))
    _github_output("provisional_review", "true" if provisional_review else "false")
    _github_output("title", str(report.get("notification_title", "Debt/NOK report")).replace("\n", " "))
    _github_output("asof", str(report.get("asof") or "unknown"))
    _github_output("report_date", str(report.get("report_date") or "unknown"))

    print(
        f"Debt/NOK {report['model_version']} · informe={report.get('report_date')} · "
        f"oficial={report.get('asof')}:{report['alert']['level']} · "
        f"provisional={fast_lane.get('asof')}:{fast_lane.get('raw_provisional_level')} · "
        f"bridge={fast_lane.get('bridge', {}).get('status')} · "
        f"review={provisional_review} · notify={notify}"
    )
    for series_id, error in sorted(factor_errors.items()):
        print(f"{series_id} warning: {error}", file=sys.stderr)
    for source_id, error in sorted(fast_lane.get("bridge", {}).get("errors", {}).items()):
        print(f"fast bridge {source_id} warning: {error}", file=sys.stderr)
    if not residual_points:
        print("Official NOK residual unavailable: operational coverage remains partial", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
