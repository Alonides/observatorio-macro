#!/usr/bin/env python3
"""Prueba de conectividad de las fuentes críticas desde GitHub Actions."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from observatorio.official import CORE_SERIES, fetch_series  # noqa: E402


def main() -> int:
    failed = []
    for series_id in sorted(CORE_SERIES):
        try:
            points = fetch_series(series_id)
            print(f"OK {series_id}: {points[-1]}")
        except Exception as exc:
            failed.append(series_id)
            print(f"ERROR {series_id}: {exc}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

