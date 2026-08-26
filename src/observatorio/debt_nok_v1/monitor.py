"""Operational Debt/NOK monitor v1.0.

This module turns the validated research classifier into an explicit operational
state without changing the underlying v0.4.1 scores.  It is deliberately
rule-based and auditable: no language model or opaque probability is used.
"""

from __future__ import annotations

from datetime import date
from typing import Mapping, Sequence

from ..debt_nok_v04.regime import evaluate_regimes as evaluate_core

MODEL_VERSION = "1.0.0"
CORE_MODEL_VERSION = "0.4.1"

LEVELS = {
    "normal": {"rank": 0, "label": "Normal", "tone": "green"},
    "watch": {"rank": 1, "label": "Vigilancia", "tone": "amber"},
    "alert": {"rank": 2, "label": "Alerta", "tone": "orange"},
    "critical": {"rank": 3, "label": "Crítico", "tone": "red"},
}

BLOCK_LABELS = {
    "urp": "Rechazo USA",
    "urr": "Persistencia USA",
    "dss": "Escasez de dólares",
    "nks": "Estrés NOK",
    "nrs": "Reversión NOK",
}

URR_SCORES = {
    "inactive": 0.0,
    "rejection_pulse": 50.0,
    "us_discrimination": 75.0,
    "rejection_regime": 100.0,
}


def _number(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _block(result: dict, key: str) -> dict:
    raw = result.get(key) if isinstance(result, dict) else None
    raw = raw if isinstance(raw, dict) else {}
    if key == "urr":
        state = str(raw.get("state") or "inactive")
        score = URR_SCORES.get(state, 0.0)
        coverage = 1.0 if raw else 0.0
    elif key == "nrs":
        state = str(raw.get("state") or "inactive")
        score = _number(raw.get("operational_score"), 0.0)
        coverage = 1.0 if raw else 0.0
    else:
        state = str(raw.get("state") or "insufficient_data")
        score = _number(raw.get("score"), 0.0)
        coverage = _number(raw.get("coverage"), 0.0)
    return {
        "key": key.upper(),
        "label": BLOCK_LABELS[key],
        "score": round(max(0.0, min(100.0, score)), 2),
        "state": state,
        "coverage": round(max(0.0, min(1.0, coverage)), 3),
    }


def classify_level(result: dict) -> tuple[str, list[str]]:
    """Return the operational level and the precise reasons that activated it."""
    urp = _block(result, "urp")
    urr = _block(result, "urr")
    dss = _block(result, "dss")
    nks = _block(result, "nks")
    nrs = _block(result, "nrs")

    reasons: list[str] = []
    critical = False
    alert = False
    watch = False

    if urr["state"] == "rejection_regime":
        critical = True
        reasons.append("URR confirma un régimen persistente de rechazo estadounidense")
    if nks["score"] >= 80.0:
        critical = True
        reasons.append(f"NKS alcanza {nks['score']:.1f}")
    if nrs["state"] == "confirmed":
        critical = True
        reasons.append("NRS confirma una reversión noruega posterior al shock")

    if urr["state"] == "us_discrimination":
        alert = True
        reasons.append("URR detecta discriminación específica contra activos estadounidenses")
    if urp["score"] >= 60.0:
        alert = True
        reasons.append(f"URP alcanza {urp['score']:.1f}")
    if dss["score"] >= 70.0:
        alert = True
        reasons.append(f"DSS alcanza {dss['score']:.1f}")
    if nks["score"] >= 65.0:
        alert = True
        reasons.append(f"NKS entra en estrés severo ({nks['score']:.1f})")

    if urr["state"] == "rejection_pulse":
        watch = True
        reasons.append("URR registra un pulso de rechazo no persistente")
    if urp["score"] >= 40.0:
        watch = True
        reasons.append(f"URP entra en vigilancia ({urp['score']:.1f})")
    if dss["score"] >= 50.0:
        watch = True
        reasons.append(f"DSS entra en vigilancia ({dss['score']:.1f})")
    if nks["score"] >= 35.0:
        watch = True
        reasons.append(f"NKS entra en vigilancia ({nks['score']:.1f})")

    if critical:
        return "critical", reasons
    if alert:
        return "alert", reasons
    if watch:
        return "watch", reasons
    return "normal", ["Ningún bloque operativo supera sus umbrales de vigilancia"]


def _summary(level: str, reasons: Sequence[str]) -> str:
    if level == "critical":
        return "La configuración exige revisión humana inmediata. " + "; ".join(reasons) + "."
    if level == "alert":
        return "Se ha activado una alerta material. " + "; ".join(reasons) + "."
    if level == "watch":
        return "Hay señales que merecen seguimiento reforzado, pero no una ruptura confirmada. " + "; ".join(reasons) + "."
    return "El detector no identifica actualmente una configuración de crisis de deuda/dólar ni estrés material de NOK."


def evaluate_operational(
    series: Mapping[str, Sequence[Mapping[str, object]]],
    asof: str | date | None = None,
) -> dict:
    result = evaluate_core(series, asof=asof)
    core_version = result.get("model_version")
    level, reasons = classify_level(result)
    blocks = {key.upper(): _block(result, key) for key in ("urp", "urr", "dss", "nks", "nrs")}
    data_coverage = result.get("data_coverage") if isinstance(result.get("data_coverage"), dict) else {}
    required_keys = ("urp_core", "relative_us", "nok_core", "norway_funding", "nok_residual")
    missing = sorted(key for key in required_keys if data_coverage.get(key) is False)
    optional_missing = sorted(
        key for key, available in data_coverage.items()
        if key not in required_keys and available is False
    )
    result["core_model_version"] = core_version or CORE_MODEL_VERSION
    result["model_version"] = MODEL_VERSION
    result["operational"] = {
        "level": level,
        **LEVELS[level],
        "reasons": reasons,
        "summary": _summary(level, reasons),
        "blocks": blocks,
        "data_quality": "complete" if not missing else "partial",
        "missing_confirmations": missing,
        "optional_confirmations_missing": optional_missing,
        "notification_required": LEVELS[level]["rank"] >= LEVELS["alert"]["rank"],
    }
    result["method_note_v1"] = (
        "The operational layer does not alter the validated v0.4.1 scores. It "
        "maps them to normal/watch/alert/critical states using declared rules."
    )
    return result


__all__ = [
    "BLOCK_LABELS",
    "CORE_MODEL_VERSION",
    "LEVELS",
    "MODEL_VERSION",
    "classify_level",
    "evaluate_operational",
]
