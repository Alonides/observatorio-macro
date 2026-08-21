"""Orquestación de la recogida, conservación y publicación."""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, date
from pathlib import Path

from .catalog import ALL_SERIES, DERIVED_SERIES, SERIES
from .derive import derive_series
from .engine import evaluate, derived_metrics
from .methodology import load_methodology, manifest
from .official import CORE_SERIES, fetch_series
from .quality import quality_status, age_days
from .state_engine import evaluate_state


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
METHODOLOGY = load_methodology()


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
    for point in previous:
        if not isinstance(point, dict) or point.get("date") is None or point.get("value") is None:
            continue
        day = str(point["date"])
        by_day[day] = dict(point)
        by_day[day]["date"] = day
    for point in incoming:
        if not isinstance(point, dict) or point.get("date") is None or point.get("value") is None:
            continue
        day = str(point["date"])
        existing = by_day.get(day)
        changed = existing is not None and existing.get("value") != point["value"]
        merged = {
            "date": day,
            "value": point["value"],
            "retrieved_at": (
                point.get("retrieved_at")
                if changed or existing is None
                else existing.get("retrieved_at") or point.get("retrieved_at")
            ),
            "published_at": point.get("published_at") or (existing or {}).get("published_at"),
            "revision": int((existing or {}).get("revision", 0)) + int(changed),
        }
        by_day[day] = {key: value for key, value in merged.items() if value is not None}
    return [by_day[day] for day in sorted(by_day)][-max_points:]


def _not_after(points: list[dict], as_of: date) -> list[dict]:
    """Excluye periodos futuros; una tasa ya anunciada no es un dato observado."""
    output = []
    for point in points:
        try:
            if date.fromisoformat(str(point.get("date"))) <= as_of:
                output.append(point)
        except (TypeError, ValueError):
            continue
    return output


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
                received = _not_after(future.result(), today)
                points = [{**point, "retrieved_at": now.isoformat()} for point in received]
                prior = _not_after(previous.get(spec.id, []), today)
                collected[spec.id] = _merge_points(prior, points, max_points)
                print(
                    f"OK {spec.id}: {len(received)} nuevas/recibidas; "
                    f"{len(collected[spec.id])} conservadas",
                    flush=True,
                )
            except Exception as exc:  # aislamiento deliberado por fuente/serie
                fallback = _not_after(previous.get(spec.id, []), today)[-max_points:]
                if fallback:
                    collected[spec.id] = fallback
                errors.append({"series_id": spec.id, "error": str(exc), "fallback_used": bool(fallback)})
                print(f"ERROR {spec.id}: {exc}", flush=True)

    errors.sort(key=lambda item: item["series_id"])

    derived = derive_series(collected)
    for spec in DERIVED_SERIES:
        incoming = [
            {**point, "retrieved_at": now.isoformat()}
            for point in derived.get(spec.id, [])
        ]
        collected[spec.id] = _merge_points(previous.get(spec.id, []), incoming, max_points)

    snapshots = []
    for spec in ALL_SERIES:
        points = collected.get(spec.id, [])
        if not points:
            snapshots.append({
                **spec.to_dict(),
                "value": None,
                "period_date": None,
                "observation_date": None,
                "published_at": None,
                "retrieved_at": None,
                "revision": None,
                "age_days": None,
                "quality": "missing",
            })
            continue
        point = points[-1]
        snapshots.append({
            **spec.to_dict(),
            "value": point["value"],
            "period_date": point["date"],
            "observation_date": point["date"],
            "published_at": point.get("published_at"),
            "retrieved_at": point.get("retrieved_at"),
            "revision": point.get("revision", 0),
            "age_days": age_days(point["date"], today),
            "quality": quality_status(spec, point["date"], today),
        })

    missing_core = sorted(series_id for series_id in CORE_SERIES if not collected.get(series_id))
    operational = not missing_core
    methodology_manifest = manifest(METHODOLOGY)
    payload = {
        "schema_version": 3,
        "generated_at": now.isoformat(),
        "code_commit": os.environ.get("GITHUB_SHA"),
        "methodology": methodology_manifest,
        "status": "ok" if not errors else "operational_partial" if operational else "failed",
        "operational": operational,
        "missing_core": missing_core,
        "series_ok": sum(1 for item in snapshots if item["value"] is not None),
        "series_total": len(ALL_SERIES),
        "errors": errors,
        "derived": derived_metrics(collected),
        "regime": evaluate(collected),
        "structural_state": evaluate_state(collected),
        "series": snapshots,
    }
    _atomic_json(DATA_DIR / "series.json", {
        "schema_version": 3,
        "generated_at": now.isoformat(),
        "code_commit": os.environ.get("GITHUB_SHA"),
        "methodology": methodology_manifest,
        "series": collected,
    })
    _atomic_json(DATA_DIR / "latest.json", payload)
    return payload
