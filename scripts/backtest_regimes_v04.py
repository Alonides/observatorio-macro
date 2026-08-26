#!/usr/bin/env python3
"""Fetch or load history and run the continuous debt/NOK v0.4 backtest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from observatorio.debt_nok_v04.backtest import run_continuous_backtest
from observatorio.debt_nok_v04.history import (
    fetch_history_dataset,
    write_history_dataset,
)
from observatorio.debt_nok_v04.scenarios import synthetic_results


def _load_series(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    series = payload.get("series")
    if not isinstance(series, dict):
        raise ValueError(f"{path}: expected an object under 'series'")
    return series


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/backtest_series_v04.json")
    parser.add_argument("--output", default="data/regime_backtest_v04.json")
    parser.add_argument("--start", default="2006-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--synthetic-only", action="store_true")
    parser.add_argument("--include-history", action="store_true")
    args = parser.parse_args()

    input_path = ROOT / args.input
    output_path = ROOT / args.output

    if args.synthetic_only:
        _write(output_path, {"model_version": "0.4.0", "synthetic": synthetic_results()})
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
