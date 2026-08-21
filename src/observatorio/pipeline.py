"""Orquestación de la recogida, conservación y publicación."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, date
from pathlib import Path

from .catalog import SERIES
from .engine import evaluate, derived_metrics
from .fred import fetch_series
from .quality import quality_status, age_days


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _atomic_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def collect(fetcher=fetch_series, now: datetime | None = None, max_points: int = 900, workers: int = 8) -> dict:
    now = now or datetime.now(timezone.utc)
    today = now.date()
    previous = _load_json(DATA_DIR / "series.json", {"series": {}}).get("series", {})
    collected: dict[str, list[dict]] = {}
    errors: list[dict] = []

    # FRED sirve cada serie en una petición independiente. La concurrencia es
    # acotada para acelerar la carga sin castigar la fuente ni ocultar fallos.
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="fred") as pool:
        futures = {pool.submit(fetcher, spec.id): spec for spec in SERIES}
        for future in as_completed(futures):
            spec = futures[future]
            try:
                points = future.result()
                collected[spec.id] = points[-max_points:]
                print(f"OK {spec.id}: {len(collected[spec.id])} observaciones", flush=True)
            except Exception as exc:  # aislamiento deliberado por fuente/serie
                fallback = previous.get(spec.id, [])
                if fallback:
                    collected[spec.id] = fallback
                errors.append({"series_id": spec.id, "error": str(exc), "fallback_used": bool(fallback)})
                print(f"ERROR {spec.id}: {exc}", flush=True)

    errors.sort(key=lambda item: item["series_id"])

    snapshots = []
    for spec in SERIES:
        points = collected.get(spec.id, [])
        if not points:
            snapshots.append({**spec.to_dict(), "value": None, "observation_date": None, "age_days": None, "quality": "missing"})
            continue
        point = points[-1]
        snapshots.append({
            **spec.to_dict(),
            "value": point["value"],
            "observation_date": point["date"],
            "age_days": age_days(point["date"], today),
            "quality": quality_status(spec, point["date"], today),
        })

    payload = {
        "schema_version": 1,
        "generated_at": now.isoformat(),
        "status": "ok" if not errors else "partial",
        "series_ok": sum(1 for item in snapshots if item["value"] is not None),
        "series_total": len(SERIES),
        "errors": errors,
        "derived": derived_metrics(collected),
        "regime": evaluate(collected),
        "series": snapshots,
    }
    _atomic_json(DATA_DIR / "series.json", {"schema_version": 1, "generated_at": now.isoformat(), "series": collected})
    _atomic_json(DATA_DIR / "latest.json", payload)
    return payload
