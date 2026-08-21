#!/usr/bin/env python3
"""Prueba de conectividad de las fuentes críticas desde GitHub Actions."""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from observatorio.catalog import SERIES  # noqa: E402
from observatorio.official import CORE_SERIES, fetch_series  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="comprueba el catálogo completo")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    selected = sorted(spec.id for spec in SERIES) if args.all else sorted(CORE_SERIES)
    failed = []
    with ThreadPoolExecutor(max_workers=args.workers, thread_name_prefix="smoke") as pool:
        futures = {pool.submit(fetch_series, series_id): series_id for series_id in selected}
        for future in as_completed(futures):
            series_id = futures[future]
            try:
                points = future.result()
                print(f"OK {series_id}: {len(points)} observaciones; última {points[-1]}")
            except Exception as exc:
                failed.append(series_id)
                print(f"ERROR {series_id}: {exc}", file=sys.stderr)
    print(f"Resultado: {len(selected) - len(failed)}/{len(selected)} series accesibles")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
