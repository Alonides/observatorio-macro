#!/usr/bin/env python3
"""Entrada de línea de comandos para la ingestión diaria."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from observatorio.pipeline import collect  # noqa: E402


def main() -> int:
    result = collect()
    print(f"Carga {result['status']}: {result['series_ok']}/{result['series_total']} series")
    for error in result["errors"]:
        print(f"- {error['series_id']}: {error['error']}", file=sys.stderr)
    # La carga parcial es publicable si al menos el 70 % de las series conserva
    # un dato válido. Así una fuente aislada no bloquea el observatorio.
    return 0 if result["series_ok"] >= result["series_total"] * 0.70 else 2


if __name__ == "__main__":
    raise SystemExit(main())

