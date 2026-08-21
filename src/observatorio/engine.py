"""Motor explicable de hipótesis y umbrales.

Los umbrales se declaran por adelantado. No son probabilidades ni consejos de
inversión. Su función es obligar al observatorio a distinguir señales que suelen
mezclarse en el relato.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, timedelta
from statistics import median


WINDOW_DAYS = 92
THRESHOLDS = {
    "dollar_change_pct_max": -5.0,
    "real_10y_change_pp_min": 0.50,
    "breakeven_10y_change_pp_min": 0.30,
    "sofr_iorb_spread_pp_min": 0.20,
    "vix_stress_min": 35.0,
    "global_peer_median_change_pp_min": 0.30,
    "us_vs_peer_excess_change_pp_min": 0.35,
}


@dataclass
class Signal:
    key: str
    label: str
    active: bool | None
    value: float | None
    threshold: str
    explanation: str

    def to_dict(self) -> dict:
        return asdict(self)


def _latest(points: list[dict]) -> float | None:
    return points[-1]["value"] if points else None


def _change(points: list[dict], days: int = WINDOW_DAYS, percent: bool = False) -> float | None:
    if len(points) < 2:
        return None
    latest_date = date.fromisoformat(points[-1]["date"])
    cutoff = latest_date - timedelta(days=days)
    prior = next((p for p in reversed(points[:-1]) if date.fromisoformat(p["date"]) <= cutoff), None)
    if prior is None:
        return None
    delta = points[-1]["value"] - prior["value"]
    if percent:
        return None if prior["value"] == 0 else delta / prior["value"] * 100
    return delta


def _signal(key: str, label: str, value: float | None, predicate, threshold: str, explanation: str) -> Signal:
    return Signal(key, label, None if value is None else bool(predicate(value)), value, threshold, explanation)


def evaluate(series: dict[str, list[dict]]) -> dict:
    dollar_change = _change(series.get("DTWEXBGS", []), percent=True)
    real_change = _change(series.get("DFII10", []))
    breakeven_change = _change(series.get("T10YIE", []))

    sofr = _latest(series.get("SOFR", []))
    iorb = _latest(series.get("IORB", []))
    spread = None if sofr is None or iorb is None else sofr - iorb
    stress = _latest(series.get("VIXCLS", []))

    triple = [
        _signal("dollar", "Dólar amplio a la baja", dollar_change,
                lambda x: x <= THRESHOLDS["dollar_change_pct_max"],
                "≤ −5 % en 92 días", "Posible debilitamiento del denominador."),
        _signal("real_yield", "Rendimiento real a la alza", real_change,
                lambda x: x >= THRESHOLDS["real_10y_change_pp_min"],
                "≥ +50 pb en 92 días", "El mercado exige más rentabilidad real."),
        _signal("breakeven", "Inflación implícita al alza", breakeven_change,
                lambda x: x >= THRESHOLDS["breakeven_10y_change_pp_min"],
                "≥ +30 pb en 92 días", "Sube simultáneamente la compensación inflacionaria."),
    ]
    confirmations = [
        _signal("repo", "Tensión monetaria SOFR−IORB", spread,
                lambda x: x >= THRESHOLDS["sofr_iorb_spread_pp_min"],
                "≥ +20 pb", "Confirma tensión de financiación, no solo movimiento de precios."),
        _signal("stress", "Pérdida de la función refugio / estrés", stress,
                lambda x: x >= THRESHOLDS["vix_stress_min"],
                "VIX ≥ 35", "Filtro conservador: exige estrés de mercado además del movimiento de precios."),
    ]

    us_change = _change(series.get("DGS10", []))
    peer_ids = ("IRLTLT01JPM156N", "IRLTLT01DEM156N", "IRLTLT01GBM156N", "IRLTLT01NOM156N", "IRLTLT01EZM156N")
    peer_changes = [v for v in (_change(series.get(i, [])) for i in peer_ids) if v is not None]
    peer_median = median(peer_changes) if peer_changes else None
    excess = None if us_change is None or peer_median is None else us_change - peer_median

    global_signal = _signal(
        "global_duration", "Reprecio global de duración", peer_median,
        lambda x: x >= THRESHOLDS["global_peer_median_change_pp_min"],
        "mediana pares ≥ +30 pb en 92 días",
        "Japón, Alemania, Reino Unido, Noruega y eurozona sirven como cesta de pares.",
    )
    us_specific = _signal(
        "us_specific", "Prima estadounidense relativa", excess,
        lambda x: x >= THRESHOLDS["us_vs_peer_excess_change_pp_min"],
        "EE. UU.−pares ≥ +35 pb en 92 días",
        "Busca deterioro relativo y no solo un movimiento mundial de duración.",
    )

    triple_active = sum(s.active is True for s in triple)
    confirmation_active = any(s.active is True for s in confirmations)
    h0 = global_signal.active is True and us_specific.active is not True
    h1 = triple_active == 3 and (confirmation_active or us_specific.active is True)
    if h0 and h1:
        regime = "H2"
        label = "Choque global con componente específico estadounidense"
    elif h1:
        regime = "H1"
        label = "Señal condicionada de pérdida de confianza"
    elif h0:
        regime = "H0"
        label = "Reprecio global de la duración"
    else:
        regime = "INDETERMINADO"
        label = "Evidencia insuficiente o mixta"

    return {
        "regime": regime,
        "label": label,
        "triple_active": triple_active,
        "confirmation_active": confirmation_active,
        "signals": [s.to_dict() for s in triple + confirmations + [global_signal, us_specific]],
        "thresholds": THRESHOLDS,
        "method_note": "H1 exige la señal triple y al menos una confirmación de liquidez, estrés o prima relativa. H2 exige además un choque global de duración.",
    }


def derived_metrics(series: dict[str, list[dict]]) -> list[dict]:
    def current(series_id: str) -> float | None:
        return _latest(series.get(series_id, []))

    dgs2, dgs10, dgs30 = current("DGS2"), current("DGS10"), current("DGS30")
    debt, gdp = current("GFDEBTN"), current("GDP")
    metrics = []
    if dgs2 is not None and dgs10 is not None:
        metrics.append({"id": "US_2S10S", "title": "Pendiente EE. UU. 2–10", "value": round((dgs10 - dgs2) * 100, 1), "unit": "pb"})
    if dgs2 is not None and dgs30 is not None:
        metrics.append({"id": "US_2S30S", "title": "Pendiente EE. UU. 2–30", "value": round((dgs30 - dgs2) * 100, 1), "unit": "pb"})
    if debt is not None and gdp is not None and gdp:
        # Ambas series están en millones/miles de millones respectivamente.
        metrics.append({"id": "US_DEBT_GDP", "title": "Deuda federal bruta / PIB", "value": round(debt / (gdp * 1000) * 100, 1), "unit": "%"})
    capex_ids = ("CAPEX_MSFT", "CAPEX_GOOG", "CAPEX_AMZN", "CAPEX_META", "CAPEX_ORCL")
    capex = [current(series_id) for series_id in capex_ids]
    capex_available = [value for value in capex if value is not None]
    if len(capex_available) >= 3:
        metrics.append({
            "id": "AI_CAPEX_QUARTER",
            "title": f"Capex último trimestre disponible · {len(capex_available)}/5 hyperscalers",
            "value": round(sum(capex_available), 1),
            "unit": "miles de millones USD",
        })
    return metrics
