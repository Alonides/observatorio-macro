"""Carga, valida y firma la especificacion metodologica ejecutable."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = ROOT / "methodology.yml"


class MethodologyError(RuntimeError):
    pass


def _canonical_bytes(payload: dict) -> bytes:
    def encode(value):
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        raise TypeError(f"Tipo no serializable en metodologia: {type(value).__name__}")

    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=encode,
    ).encode("utf-8")


def methodology_hash(payload: dict) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _validate_parameter(name: str, parameter: dict) -> None:
    required = {"value", "unit", "direction", "frozen_on", "calibration_start", "calibration_end", "rationale"}
    missing = sorted(required - set(parameter))
    if missing:
        raise MethodologyError(f"{name}: faltan campos metodologicos: {', '.join(missing)}")


def validate_methodology(payload: dict) -> None:
    for key in ("schema_version", "methodology", "governance", "hypotheses", "event_engine", "state_engine"):
        if key not in payload:
            raise MethodologyError(f"methodology.yml: falta {key}")
    expected = {"H0", "H1", "H2", "MIXED", "INDETERMINATE"}
    if set(payload["hypotheses"]) != expected:
        raise MethodologyError("methodology.yml: las hipotesis canonicas no coinciden")
    event = payload["event_engine"]
    for key, parameter in event["triple_alert"].items():
        _validate_parameter(f"triple_alert.{key}", parameter)
    for key, parameter in event["confirmations"].items():
        _validate_parameter(f"confirmations.{key}", parameter)
    _validate_parameter("global_duration.minimum_markets_rising", event["global_duration"]["minimum_markets_rising"])
    _validate_parameter("global_duration.minimum_rise_pp", event["global_duration"]["minimum_rise_pp"])
    _validate_parameter("us_specific.transition_excess_change_pp_min", event["us_specific"]["transition_excess_change_pp_min"])
    target = event["us_specific"]["target_model"]
    if target.get("status") == "calibrated_candidate":
        result = target.get("calibration_result") or {}
        required_result = {
            "observations", "intercept_pp", "betas", "r_squared", "rmse_pp",
            "h0_p90_pp", "h1_p95_pp",
        }
        missing = sorted(required_result - set(result))
        if missing:
            raise MethodologyError(f"us_specific.target_model: faltan resultados: {', '.join(missing)}")
        if set(result["betas"]) != set(target["regression"]["predictors"]):
            raise MethodologyError("us_specific.target_model: los coeficientes no coinciden con la cesta congelada")
        if float(result["h1_p95_pp"]) <= float(result["h0_p90_pp"]):
            raise MethodologyError("us_specific.target_model: p95 debe ser mayor que p90")
        if target.get("artifact_sha256") is None:
            raise MethodologyError("us_specific.target_model: falta la huella del artefacto")
    if payload["governance"].get("event_and_state_must_remain_separate") is not True:
        raise MethodologyError("methodology.yml: los motores de acto y estado deben permanecer separados")


def load_methodology(path: Path | None = None) -> dict:
    source = path or DEFAULT_PATH
    try:
        payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise MethodologyError(f"No se pudo leer {source}: {exc}") from exc
    if not isinstance(payload, dict):
        raise MethodologyError(f"{source}: la raiz debe ser un objeto")
    validate_methodology(payload)
    return payload


def manifest(payload: dict) -> dict:
    meta = payload["methodology"]
    scalar = lambda value: value.isoformat() if isinstance(value, (date, datetime)) else value
    return {
        "id": meta["id"],
        "version": meta["version"],
        "status": meta["status"],
        "effective_from": scalar(meta.get("effective_from")),
        "calibration_cutoff": scalar(meta.get("calibration_cutoff")),
        "hash_algorithm": meta["canonical_hash"],
        "sha256": methodology_hash(payload),
        "semantic_reference": meta.get("semantic_reference"),
    }


def parameter_value(payload: dict, section: str, key: str) -> float:
    return float(payload["event_engine"][section][key]["value"])
