"""Operational Debt/NOK monitor v1.0.2.

This module maps the validated v0.4.1 core to explicit operational states. The
v1.0.2 change is temporal rather than mathematical: URP, URR, DSS, NKS and NRS
are evaluated at their own latest complete input dates and carry visible
freshness metadata.
"""

from __future__ import annotations

from datetime import date
from typing import Mapping, Sequence

from .freshness import evaluate_fresh_regimes, previous_block_dates

MODEL_VERSION = "1.0.2"
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
    state = str(raw.get("state") or "insufficient_data")
    freshness = (
        result.get("freshness", {}).get("blocks", {}).get(key.upper(), {})
        if isinstance(result, dict)
        else {}
    )
    if key == "urr":
        score = URR_SCORES.get(state, 0.0)
        coverage = 0.0 if state == "insufficient_data" else 1.0
    elif key == "nrs":
        score = _number(raw.get("operational_score"), 0.0)
        coverage = 0.0 if state == "insufficient_data" else 1.0
    else:
        score = _number(raw.get("score"), 0.0)
        coverage = _number(raw.get("coverage"), 0.0)
    return {
        "key": key.upper(),
        "label": BLOCK_LABELS[key],
        "score": round(max(0.0, min(100.0, score)), 2),
        "state": state,
        "coverage": round(max(0.0, min(1.0, coverage)), 3),
        "asof": raw.get("asof") or freshness.get("asof"),
        "freshness_status": freshness.get("status", "unavailable"),
        "freshness_label": freshness.get("label", "No disponible"),
        "business_day_lag": freshness.get("business_day_lag"),
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
    if nrs["state"] == "confirmed":
        alert = True
        reasons.append(
            "NRS confirma una reversión noruega posterior al shock; es un cambio "
            "de régimen relevante, pero no implica por sí solo deterioro sistémico"
        )

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
    block_asof: Mapping[str, str | date | None] | None = None,
) -> dict:
    result = evaluate_fresh_regimes(series, asof=asof, block_asof=block_asof)
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
    freshness = result.get("freshness") if isinstance(result.get("freshness"), dict) else {}
    result["core_model_version"] = core_version or CORE_MODEL_VERSION
    result["model_version"] = MODEL_VERSION
    result["operational"] = {
        "level": level,
        **LEVELS[level],
        "reasons": reasons,
        "summary": _summary(level, reasons),
        "blocks": blocks,
        "data_quality": "complete" if not missing else "partial",
        "data_freshness": freshness.get("quality", "unavailable"),
        "data_freshness_label": freshness.get("label", "No disponible"),
        "missing_confirmations": missing,
        "optional_confirmations_missing": optional_missing,
        "notification_required": LEVELS[level]["rank"] >= LEVELS["alert"]["rank"],
    }
    result["method_note_v1"] = (
        "The operational layer does not alter the validated v0.4.1 scores. It "
        "maps them to normal/watch/alert/critical states and evaluates each block "
        "at its own latest complete input date. A confirmed NRS is a material "
        "regime-change alert, not a critical loss signal."
    )
    return result


__all__ = [
    "BLOCK_LABELS",
    "CORE_MODEL_VERSION",
    "LEVELS",
    "MODEL_VERSION",
    "classify_level",
    "evaluate_operational",
    "previous_block_dates",
]
