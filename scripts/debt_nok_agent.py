#!/usr/bin/env python3
"""Scheduled operational agent for the Debt/NOK monitor.

The agent reads the repository's daily market history, enriches it with SEK/USD,
calculates the causal NOK residual, evaluates v1.0, writes the web payload and
emits GitHub Actions outputs for weekly delivery or material alerts.
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

from observatorio.debt_nok_v04.residual import build_nok_residual  # noqa: E402
from observatorio.debt_nok_v1.report import build_report  # noqa: E402
from observatorio.official import _fed_package  # noqa: E402

DATA_DIR = ROOT / "data"
MONITOR_DIR = DATA_DIR / "debt_nok"


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


def _merge_points(*groups: list[dict], limit: int = 1200) -> list[dict]:
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


def _fetch_sek(existing: list[dict]) -> tuple[list[dict], str | None]:
    try:
        points = _fed_package("H10", "rates", 1200).get("RXI_N.B.SD", [])
        if not points:
            raise RuntimeError("Federal Reserve H.10 returned no SEK/USD observations")
        return _merge_points(existing, points), None
    except Exception as exc:  # the monitor remains readable with the last valid history
        return _merge_points(existing), str(exc)


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
    parser.add_argument("--no-network", action="store_true", help="Use only the previously cached SEK series")
    args = parser.parse_args()

    source = _load(DATA_DIR / "series.json", {})
    series = source.get("series")
    if not isinstance(series, dict):
        raise SystemExit("data/series.json does not contain a series object")

    prior_history = _load(MONITOR_DIR / "history.json", {"series": {}}).get("series", {})
    previous_sek = prior_history.get("DEXSDUS", []) if isinstance(prior_history, dict) else []
    if args.no_network:
        sek = _merge_points(previous_sek)
        sek_error = None if sek else "network disabled and no cached SEK/USD history exists"
    else:
        sek, sek_error = _fetch_sek(previous_sek)
    if sek:
        series = dict(series)
        series["DEXSDUS"] = sek

    residual = build_nok_residual(series)
    if residual.get("points"):
        series["NOK_RESIDUAL_Z20"] = residual["points"]

    report = build_report(series, mode=args.mode)
    report["source_status"] = {
        "sek_usd": "ok" if sek else "missing",
        "sek_error": sek_error,
        "residual_points": len(residual.get("points", [])),
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
        "schema_version": 1,
        "generated_at": report["generated_at"],
        "series": {
            "DEXSDUS": sek,
            "EURNOK": eurnok[-1200:],
            "NOKSEK": noksek[-1200:],
            "NOK_RESIDUAL_Z20": residual.get("points", [])[-1200:],
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
        f"{report['alert']['level']} · notify={notify}"
    )
    if sek_error:
        print(f"SEK/USD warning: {sek_error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
