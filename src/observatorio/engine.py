"""Motor explicable de acontecimientos y magnitudes derivadas.

Las definiciones y los parametros se cargan desde ``methodology.yml``. Cada
salida publica la version y el hash de esa especificacion. Este modulo no
calcula el estado estructural: acto y estado permanecen separados.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from statistics import median

from .methodology import load_methodology, manifest, parameter_value


METHODOLOGY = load_methodology()
EVENT_METHOD = METHODOLOGY["event_engine"]
WINDOW_DAYS = int(EVENT_METHOD["primary_window_days"])


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
    prior = next(
        (point for point in reversed(points[:-1]) if date.fromisoformat(point["date"]) <= cutoff),
        None,
    )
    if prior is None:
        return None
    delta = points[-1]["value"] - prior["value"]
    if percent:
        return None if prior["value"] == 0 else delta / prior["value"] * 100
    return delta


def _signal(key: str, label: str, value: float | None, predicate, threshold: str, explanation: str) -> Signal:
    return Signal(key, label, None if value is None else bool(predicate(value)), value, threshold, explanation)


def _context_windows(series: dict[str, list[dict]]) -> dict[str, dict]:
    """Publica ventanas auxiliares sin permitirles activar una hipotesis."""
    output = {}
    for days in EVENT_METHOD["context_windows_days"]:
        output[str(days)] = {
            "dollar_change_pct": _change(series.get("DTWEXBGS", []), days=days, percent=True),
            "real_10y_change_pp": _change(series.get("DFII10", []), days=days),
            "breakeven_10y_change_pp": _change(series.get("T10YIE", []), days=days),
            "us_10y_change_pp": _change(series.get("DGS10", []), days=days),
        }
    return output


def evaluate(series: dict[str, list[dict]]) -> dict:
    global_method = EVENT_METHOD["global_duration"]
    us_method = EVENT_METHOD["us_specific"]

    dollar_limit = parameter_value(METHODOLOGY, "triple_alert", "dollar_change_pct_max")
    real_limit = parameter_value(METHODOLOGY, "triple_alert", "real_10y_change_pp_min")
    breakeven_limit = parameter_value(METHODOLOGY, "triple_alert", "breakeven_10y_change_pp_min")
    repo_limit = parameter_value(METHODOLOGY, "confirmations", "sofr_iorb_spread_pp_min")
    vix_limit = parameter_value(METHODOLOGY, "confirmations", "vix_stress_min")
    us_excess_limit = float(us_method["transition_excess_change_pp_min"]["value"])

    dollar_change = _change(series.get("DTWEXBGS", []), percent=True)
    real_change = _change(series.get("DFII10", []))
    breakeven_change = _change(series.get("T10YIE", []))

    sofr = _latest(series.get("SOFR", []))
    iorb = _latest(series.get("IORB", []))
    spread = None if sofr is None or iorb is None else sofr - iorb
    stress = _latest(series.get("VIXCLS", []))
    equity_change = _change(series.get("SP500", []), percent=True)
    ig_oas_change = _change(series.get("BAMLC0A0CM", []))
    ig_yield_change = _change(series.get("BAMLC0A0CMEY", []))

    triple = [
        _signal(
            "dollar",
            "Dolar amplio a la baja",
            dollar_change,
            lambda value: value <= dollar_limit,
            f"≤ {dollar_limit:g} % en {WINDOW_DAYS} dias",
            "Alarma de posible debilitamiento del denominador.",
        ),
        _signal(
            "real_yield",
            "Rendimiento real al alza",
            real_change,
            lambda value: value >= real_limit,
            f"≥ +{real_limit * 100:g} pb en {WINDOW_DAYS} dias",
            "El mercado exige mas rentabilidad real.",
        ),
        _signal(
            "breakeven",
            "Inflacion implicita al alza",
            breakeven_change,
            lambda value: value >= breakeven_limit,
            f"≥ +{breakeven_limit * 100:g} pb en {WINDOW_DAYS} dias",
            "Sube simultaneamente la compensacion inflacionaria.",
        ),
    ]
    confirmations = [
        _signal(
            "repo",
            "Tension monetaria SOFR-IORB",
            spread,
            lambda value: value >= repo_limit,
            f"≥ +{repo_limit * 100:g} pb",
            "Indica tension de financiacion, no perdida de refugio por si sola.",
        ),
        _signal(
            "stress",
            "Estres general de mercado",
            stress,
            lambda value: value >= vix_limit,
            f"VIX ≥ {vix_limit:g}",
            "Contexto de estres; no prueba por si solo un deterioro del Treasury.",
        ),
    ]

    us_change = _change(series.get("DGS10", []))
    market_ids = tuple(global_method["market_series"])
    peer_ids = tuple(us_method["peer_series"])
    market_changes = {series_id: _change(series.get(series_id, [])) for series_id in market_ids}
    peer_changes = [
        market_changes[series_id]
        for series_id in peer_ids
        if market_changes.get(series_id) is not None
    ]
    peer_median = median(peer_changes) if peer_changes else None
    excess = None if us_change is None or peer_median is None else us_change - peer_median

    rise_floor = float(global_method["minimum_rise_pp"]["value"])
    minimum_markets = int(global_method["minimum_markets_rising"]["value"])
    available_markets = sum(value is not None for value in market_changes.values())
    markets_rising = sum(value is not None and value > rise_floor for value in market_changes.values())
    global_active = None if available_markets < minimum_markets else markets_rising >= minimum_markets

    global_signal = Signal(
        "global_duration",
        "Sincronismo global de duracion",
        global_active,
        peer_median,
        f"≥ {minimum_markets}/{len(market_ids)} mercados al alza en {WINDOW_DAYS} dias",
        "Estados Unidos, Japon, Alemania y Reino Unido forman la cesta de adjudicacion.",
    )
    us_specific = _signal(
        "us_specific",
        "Prima estadounidense relativa",
        excess,
        lambda value: value >= us_excess_limit,
        f"EE. UU.-pares ≥ +{us_excess_limit * 100:g} pb en {WINDOW_DAYS} dias · transicion",
        "Regla provisional hasta sustituirla por el residuo p90/p95 calibrado sobre 2003-2024.",
    )

    triple_active = sum(signal.active is True for signal in triple)
    if equity_change is None or ig_oas_change is None:
        risk_context = "UNAVAILABLE"
    elif equity_change > 0 and ig_oas_change < 0:
        risk_context = "REFLATION_COMPATIBLE"
    elif equity_change < 0 and ig_oas_change > 0:
        risk_context = "SYSTEMIC_STRESS_COMPATIBLE"
    else:
        risk_context = "DIVERGENT"
    market_stress_confirmation = risk_context == "SYSTEMIC_STRESS_COMPATIBLE"
    confirmation_active = any(signal.active is True for signal in confirmations) or market_stress_confirmation

    # Cada hipotesis exige evidencia positiva. H0 no aparece por simple descarte
    # de H1. La triple coincidencia es una alarma, nunca una sentencia.
    h1 = triple_active == 3 and us_specific.active is True and confirmation_active
    h2 = global_signal.active is True and us_specific.active is not True
    mixed = global_signal.active is True and h1
    h0 = us_specific.active is True and global_signal.active is not True and triple_active < 3

    if mixed:
        regime = "MIXED"
        label = "Choque global con componente especifico estadounidense"
    elif h1:
        regime = "H1"
        label = "Evidencia compatible con perdida de confianza"
    elif h2:
        regime = "H2"
        label = "Reprecio global de la duracion"
    elif h0:
        regime = "H0"
        label = "Evidencia compatible con prima estadounidense de oferta y plazo"
    else:
        regime = "INDETERMINATE"
        label = "Evidencia insuficiente o contradictoria"

    evidence_levels = {
        "H0": "compatible",
        "H1": "candidate",
        "H2": "compatible",
        "MIXED": "candidate",
        "INDETERMINATE": "insufficient",
    }

    return {
        "regime": regime,
        "label": label,
        "evidence_level": evidence_levels[regime],
        "context": "TRIPLE_ALERT" if triple_active == 3 else "NONE",
        "risk_context": {
            "classification": risk_context,
            "equity_change_pct": equity_change,
            "ig_oas_change_pp": ig_oas_change,
            "ig_effective_yield_change_pp": ig_yield_change,
            "is_confirmation": market_stress_confirmation,
            "note": (
                "Renta variable y credito distinguen contextos, pero no son una condicion necesaria de H1: "
                "el capital puede migrar del Treasury hacia capacidad privada estadounidense."
            ),
        },
        "triple_active": triple_active,
        "confirmation_active": confirmation_active,
        "signals": [signal.to_dict() for signal in triple + confirmations + [global_signal, us_specific]],
        "diagnostics": {
            "markets_available": available_markets,
            "markets_rising": markets_rising,
            "market_changes_pp": market_changes,
            "peer_median_change_pp": peer_median,
            "us_change_pp": us_change,
            "us_excess_change_pp": excess,
            "us_specific_rule_status": us_method["transition_excess_change_pp_min"].get("status"),
        },
        "context_windows": _context_windows(series),
        "methodology": manifest(METHODOLOGY),
        "method_note": (
            "La señal triple abre investigacion y nunca decide H1 por si sola. "
            "H0 requiere evidencia estadounidense positiva; H2 exige sincronismo global. "
            "Las ventanas de seis y doce meses son contexto, no rutas alternativas de activacion."
        ),
    }


def derived_metrics(series: dict[str, list[dict]]) -> list[dict]:
    def current(series_id: str) -> float | None:
        return _latest(series.get(series_id, []))

    dgs2, dgs10, dgs30 = current("DGS2"), current("DGS10"), current("DGS30")
    gross_debt = current("GFDEBTN")
    public_debt = current("US_DEBT_HELD_PUBLIC")
    gdp = current("GDP")
    metrics = []
    if dgs2 is not None and dgs10 is not None:
        metrics.append({
            "id": "US_2S10S",
            "title": "Pendiente EE. UU. 2-10",
            "value": round((dgs10 - dgs2) * 100, 1),
            "unit": "pb",
        })
    if dgs2 is not None and dgs30 is not None:
        metrics.append({
            "id": "US_2S30S",
            "title": "Pendiente EE. UU. 2-30",
            "value": round((dgs30 - dgs2) * 100, 1),
            "unit": "pb",
        })
    if public_debt is not None and gdp:
        metrics.append({
            "id": "US_PUBLIC_DEBT_GDP",
            "title": "Deuda en manos del publico / PIB",
            "value": round(public_debt / (gdp * 1000) * 100, 1),
            "unit": "%",
        })
    if gross_debt is not None and gdp:
        metrics.append({
            "id": "US_GROSS_DEBT_GDP",
            "title": "Deuda federal bruta / PIB",
            "value": round(gross_debt / (gdp * 1000) * 100, 1),
            "unit": "%",
        })
    capex_ids = ("CAPEX_MSFT", "CAPEX_GOOG", "CAPEX_AMZN", "CAPEX_META", "CAPEX_ORCL")
    capex = [current(series_id) for series_id in capex_ids]
    capex_available = [value for value in capex if value is not None]
    if len(capex_available) >= 3:
        metrics.append({
            "id": "AI_CAPEX_QUARTER",
            "title": f"Capex ultimo trimestre disponible · {len(capex_available)}/5 hyperscalers",
            "value": round(sum(capex_available), 1),
            "unit": "miles de millones USD",
        })
    return metrics
