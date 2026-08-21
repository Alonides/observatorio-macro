"""Orquestación de la recogida, conservación y publicación."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, date
from pathlib import Path

from .catalog import SERIES
from .engine import evaluate, derived_metrics
from .official import CORE_SERIES, fetch_series
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


def _merge_points(previous: list[dict], incoming: list[dict], max_points: int) -> list[dict]:
    """Une por fecha sin borrar historia cuando una API solo entrega el último dato."""
    by_day: dict[str, dict] = {}
    for point in [*previous, *incoming]:
        if not isinstance(point, dict) or point.get("date") is None or point.get("value") is None:
            continue
        day = str(point["date"])
        by_day[day] = {"date": day, "value": point["value"]}
    return [by_day[day] for day in sorted(by_day)][-max_points:]


def collect(fetcher=fetch_series, now: datetime | None = None, max_points: int = 900, workers: int = 8) -> dict:
    now = now or datetime.now(timezone.utc)
    today = now.date()
    previous = _load_json(DATA_DIR / "series.json", {"series": {}}).get("series", {})
    collected: dict[str, list[dict]] = {}
    errors: list[dict] = []

    # La concurrencia es acotada para acelerar la carga sin castigar a los
    # productores oficiales ni ocultar fallos individuales.
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="source") as pool:
        futures = {pool.submit(fetcher, spec.id): spec for spec in SERIES}
        for future in as_completed(futures):
            spec = futures[future]
            try:
                points = future.result()
                collected[spec.id] = _merge_points(previous.get(spec.id, []), points, max_points)
                print(
                    f"OK {spec.id}: {len(points)} nuevas/recibidas; "
                    f"{len(collected[spec.id])} conservadas",
                    flush=True,
                )
            except Exception as exc:  # aislamiento deliberado por fuente/serie
                fallback = previous.get(spec.id, [])[-max_points:]
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

    missing_core = sorted(series_id for series_id in CORE_SERIES if not collected.get(series_id))
    operational = not missing_core
    payload = {
        "schema_version": 2,
        "generated_at": now.isoformat(),
        "status": "ok" if not errors else "operational_partial" if operational else "failed",
        "operational": operational,
        "missing_core": missing_core,
        "series_ok": sum(1 for item in snapshots if item["value"] is not None),
        "series_total": len(SERIES),
        "errors": errors,
        "derived": derived_metrics(collected),
        "regime": evaluate(collected),
        "series": snapshots,
    }
    _atomic_json(DATA_DIR / "series.json", {"schema_version": 2, "generated_at": now.isoformat(), "series": collected})
    _atomic_json(DATA_DIR / "latest.json", payload)
    return payload
