#!/usr/bin/env python3
"""Genera el artefacto congelado de calibración del modelo relativo v0.2."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from observatorio.calibration import build_artifact  # noqa: E402
from observatorio.methodology import load_methodology, methodology_hash  # noqa: E402
from observatorio.official import relative_model_history  # noqa: E402


def _preregistration_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "log", "-1", "--format=%H", "--", "docs/CALIBRATION_SPEC_V02.md"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--output", default="data/calibration/us_relative_v02.json")
    args = parser.parse_args()

    as_of = date.fromisoformat(args.as_of)
    methodology = load_methodology()
    target = methodology["event_engine"]["us_specific"]["target_model"]
    if target.get("status") != "specification_frozen_pre_estimation":
        raise SystemExit(
            "La calibración solo parte del estado specification_frozen_pre_estimation; "
            "no se reestima silenciosamente un modelo ya congelado."
        )

    generated_at = datetime.now(timezone.utc).isoformat()
    print("Descargando cuatro curvas oficiales...", flush=True)
    series = relative_model_history(as_of)
    for series_id, points in series.items():
        print(f"  {series_id}: {len(points)} observaciones", flush=True)

    artifact = build_artifact(
        series,
        target,
        as_of=as_of,
        generated_at=generated_at,
        preregistration_commit=_preregistration_commit(),
        preregistration_methodology_hash=methodology_hash(methodology),
    )
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Escrito {output.relative_to(ROOT)}", flush=True)
    print(json.dumps({
        "fit": artifact["fit"],
        "thresholds": artifact["operational_thresholds"],
        "out_of_sample": artifact["horizons"]["3"]["out_of_sample"]["activations"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
