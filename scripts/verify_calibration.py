#!/usr/bin/env python3
"""Verifica sin red el artefacto congelado de calibración v0.2."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from observatorio.calibration import verify_artifact  # noqa: E402
from observatorio.methodology import load_methodology  # noqa: E402


def main() -> int:
    methodology = load_methodology()
    target = methodology["event_engine"]["us_specific"]["target_model"]
    path = ROOT / target["artifact"]
    raw = path.read_bytes()
    pinned_hash = target["artifact_sha256"]
    actual_hash = hashlib.sha256(raw).hexdigest()
    artifact = json.loads(raw)
    verification = verify_artifact(artifact, target)
    verification.update({
        "artifact": str(path.relative_to(ROOT)),
        "sha256": actual_hash,
        "pinned_sha256": pinned_hash,
        "hash_matches": actual_hash == pinned_hash,
    })
    verification["valid"] = bool(verification["valid"] and verification["hash_matches"])
    print(json.dumps(verification, ensure_ascii=False, indent=2))
    return 0 if verification["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
