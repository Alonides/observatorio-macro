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
    # Las fuentes se incorporan por capas. El job es operativo cuando están
    # presentes todas las series críticas del motor, aunque variables auxiliares
    # sigan marcadas como pendientes.
    return 0 if result["operational"] else 2



if __name__ == "__main__":
    raise SystemExit(main())
