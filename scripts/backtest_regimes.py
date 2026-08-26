#!/usr/bin/env python3
"""Fetch or load history, then run the continuous debt/NOK backtest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from observatorio.backtest import run_continuous_backtest
from observatorio.history import fetch_history_dataset, write_history_dataset
from observatorio.scenarios import synthetic_results


def _load_series(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    series = payload.get("series")
    if not isinstance(series, dict):
        raise ValueError(f"{path}: expected an object under 'series'")
    return series


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/backtest_series.json")
    parser.add_argument("--output", default="data/regime_backtest.json")
    parser.add_argument("--start", default="2006-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--synthetic-only", action="store_true")
    parser.add_argument("--include-history", action="store_true")
    args = parser.parse_args()

    input_path = ROOT / args.input
    output_path = ROOT / args.output
    if args.synthetic_only:
        payload = {"synthetic": synthetic_results()}
        _write(output_path, payload)
        print(output_path)
        return 0

    if args.fetch:
        history = fetch_history_dataset(start=args.start, end=args.end)
        write_history_dataset(input_path, history)
        series = history["series"]
    else:
        series = _load_series(input_path)

    result = run_continuous_backtest(series, include_history=args.include_history)
    result["synthetic"] = synthetic_results()
    _write(output_path, result)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
