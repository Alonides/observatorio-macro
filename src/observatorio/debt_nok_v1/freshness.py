"""Block-specific dating and freshness metadata for Debt/NOK v1.0.2.

The validated v0.4.1 equations remain untouched. This module only decides the
latest date on which each operational block can be evaluated with its own
inputs, then combines those independently dated results into one transparent
snapshot.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from typing import Mapping, Sequence

from ..debt_nok_v04.regime import MarketData, evaluate_regimes
from ..debt_nok_v04.residual import attach_nok_residual


BLOCK_KEYS = ("URP", "URR", "DSS", "NKS", "NRS")
FRESHNESS_LABELS = {
    "fresh": "Actualizado",
    "delayed": "Retrasado",
    "stale": "Obsoleto",
    "unavailable": "No disponible",
    "partial": "Parcial",
}


def _parse_day(raw: str | date | None) -> date | None:
    if raw is None:
        return None
    if isinstance(raw, date):
        return raw
    try:
        return date.fromisoformat(str(raw))
    except ValueError:
        return None


def _day(md: MarketData, series_id: str) -> date | None:
    return md.view(series_id).day()


def _iso(day: date | None) -> str | None:
    return day.isoformat() if day else None


def _business_day_lag(start: date | None, end: date | None) -> int | None:
    if start is None or end is None:
        return None
    if start >= end:
        return 0
    lag = 0
    current = start + timedelta(days=1)
    while current <= end:
        if current.weekday() < 5:
            lag += 1
        current += timedelta(days=1)
    return lag


def _status(lag: int | None) -> str:
    if lag is None:
        return "unavailable"
    if lag <= 1:
        return "fresh"
    if lag <= 3:
        return "delayed"
    return "stale"


def _minimum_complete(
    inputs: Mapping[str, date | None],
    mandatory: Sequence[str],
    any_of: Sequence[Sequence[str]] = (),
) -> date | None:
    if any(inputs.get(key) is None for key in mandatory):
        return None
    for group in any_of:
        if not any(inputs.get(key) is not None for key in group):
            return None
    available = [value for value in inputs.values() if value is not None]
    return min(available) if available else None


def _block_inputs(md: MarketData) -> tuple[dict[str, dict[str, date | None]], dict[str, date | None]]:
    risk = {
        "VIX": _day(md, "VIXCLS"),
        "SP500": _day(md, "SP500"),
    }
    us_bund = md.us_bund().day()
    no_bund = md.no_bund().day()
    eurnok = md.eurnok().day()
    noksek = md.noksek().day()

    urp = {
        "UST30": _day(md, "DGS30"),
        "BROAD_USD": _day(md, "DTWEXBGS"),
        **risk,
        "US_BUND": us_bund,
    }
    urr = {
        **urp,
        "GOLD": _day(md, "GOLDAMGBD228NLBM"),
        "REAL_10Y": _day(md, "DFII10"),
    }
    dss = {
        "UST30": _day(md, "DGS30"),
        "BROAD_USD": _day(md, "DTWEXBGS"),
        **risk,
    }
    nks = {
        "EUR_NOK": eurnok,
        "NOK_SEK": noksek,
        "NOK_RESIDUAL": _day(md, "NOK_RESIDUAL_Z20"),
        "NORWAY_BUND": no_bund,
        "NIBOR_OIS": _day(md, "NIBOR_OIS"),
    }
    nrs = {
        "EUR_NOK": eurnok,
        "NOK_SEK": noksek,
        "NOK_RESIDUAL": _day(md, "NOK_RESIDUAL_Z20"),
        "NORWAY_BUND": no_bund,
        "BRENT": _day(md, "DCOILBRENTEU"),
    }
    inputs = {"URP": urp, "URR": urr, "DSS": dss, "NKS": nks, "NRS": nrs}
    dates = {
        "URP": _minimum_complete(urp, ("UST30", "BROAD_USD"), (("VIX", "SP500"),)),
        "URR": _minimum_complete(urr, ("UST30", "BROAD_USD"), (("VIX", "SP500"),)),
        "DSS": _minimum_complete(dss, ("UST30", "BROAD_USD"), (("VIX", "SP500"),)),
        "NKS": _minimum_complete(nks, ("EUR_NOK", "NOK_SEK")),
        "NRS": _minimum_complete(nrs, ("EUR_NOK", "NOK_SEK", "NOK_RESIDUAL", "NORWAY_BUND", "BRENT")),
    }
    return inputs, dates


def _freshness(inputs: dict[str, dict[str, date | None]], dates: dict[str, date | None]) -> dict:
    all_input_dates = [
        day
        for block_inputs in inputs.values()
        for day in block_inputs.values()
        if day is not None
    ]
    latest = max(all_input_dates) if all_input_dates else None
    blocks: dict[str, dict] = {}
    for key in BLOCK_KEYS:
        lag = _business_day_lag(dates.get(key), latest)
        state = _status(lag)
        blocks[key] = {
            "asof": _iso(dates.get(key)),
            "business_day_lag": lag,
            "status": state,
            "label": FRESHNESS_LABELS[state],
            "inputs": {name: _iso(day) for name, day in inputs.get(key, {}).items() if day is not None},
        }
    available = [item for item in blocks.values() if item["business_day_lag"] is not None]
    unavailable = [key for key, item in blocks.items() if item["business_day_lag"] is None]
    if unavailable:
        quality = "partial"
    else:
        worst = max((item["business_day_lag"] for item in available), default=0)
        quality = _status(worst)
    oldest = max(
        available,
        key=lambda item: item["business_day_lag"],
        default=None,
    )
    oldest_key = next((key for key, item in blocks.items() if item is oldest), None)
    return {
        "quality": quality,
        "label": FRESHNESS_LABELS[quality],
        "latest_input_date": _iso(latest),
        "latest_block_date": _iso(max((day for day in dates.values() if day is not None), default=None)),
        "oldest_block": oldest_key,
        "oldest_block_date": oldest.get("asof") if oldest else None,
        "maximum_business_day_lag": oldest.get("business_day_lag") if oldest else None,
        "unavailable_blocks": unavailable,
        "blocks": blocks,
        "lag_definition": "Días hábiles aproximados entre la fecha del bloque y el dato de mercado más reciente.",
    }


def block_asof_dates(
    series: Mapping[str, Sequence[Mapping[str, object]]],
) -> tuple[dict[str, str | None], dict]:
    enriched, _ = attach_nok_residual(series)
    md = MarketData(enriched)
    inputs, dates = _block_inputs(md)
    metadata = _freshness(inputs, dates)
    return {key: _iso(dates[key]) for key in BLOCK_KEYS}, metadata


def previous_block_dates(
    series: Mapping[str, Sequence[Mapping[str, object]]],
    current: Mapping[str, str | date | None],
    sessions: int = 5,
) -> dict[str, str | None]:
    enriched, _ = attach_nok_residual(series)
    md = MarketData(enriched)
    references = {
        "URP": md.view("DGS30"),
        "URR": md.view("DGS30"),
        "DSS": md.view("DGS30"),
        "NKS": md.eurnok(),
        "NRS": md.eurnok(),
    }
    output: dict[str, str | None] = {}
    for key in BLOCK_KEYS:
        day = _parse_day(current.get(key) or current.get(key.lower()))
        view = references[key]
        position = view.position(day)
        prior = position - sessions if position is not None else -1
        output[key] = view.dates[prior].isoformat() if prior >= 0 else None
    return output


def _missing_block(key: str) -> dict:
    if key == "URR":
        return {
            "asof": None,
            "state": "insufficient_data",
            "pulse": False,
            "discrimination": False,
            "rejection_regime": False,
        }
    return {
        "asof": None,
        "score": None,
        "state": "insufficient_data",
        "coverage": 0.0,
    }


def evaluate_fresh_regimes(
    series: Mapping[str, Sequence[Mapping[str, object]]],
    asof: str | date | None = None,
    block_asof: Mapping[str, str | date | None] | None = None,
) -> dict:
    enriched, residual_diagnostics = attach_nok_residual(series)
    md = MarketData(enriched)
    inputs, derived_dates = _block_inputs(md)

    if asof is not None:
        fixed = _parse_day(asof)
        dates = {key: fixed for key in BLOCK_KEYS}
    elif block_asof is not None:
        dates = {
            key: _parse_day(block_asof.get(key) or block_asof.get(key.lower()))
            for key in BLOCK_KEYS
        }
    else:
        dates = derived_dates

    metadata = _freshness(inputs, dates)
    valid_dates = [day for day in dates.values() if day is not None]
    if not valid_dates:
        return {
            "model_version": "0.4.1",
            "asof": None,
            "status": "insufficient_data",
            "block_asof": {key: None for key in BLOCK_KEYS},
            "freshness": metadata,
            "urp": _missing_block("URP"),
            "urr": _missing_block("URR"),
            "dss": _missing_block("DSS"),
            "nks": _missing_block("NKS"),
            "nrs": _missing_block("NRS"),
        }

    cache: dict[date, dict] = {}

    def result_at(day: date) -> dict:
        if day not in cache:
            cache[day] = evaluate_regimes(enriched, asof=day)
        return cache[day]

    latest_block_date = max(valid_dates)
    combined = deepcopy(result_at(latest_block_date))
    for key in BLOCK_KEYS:
        day = dates[key]
        if day is None:
            raw = _missing_block(key)
        else:
            raw = deepcopy(result_at(day).get(key.lower()) or _missing_block(key))
            raw["asof"] = day.isoformat()
        combined[key.lower()] = raw

    combined["asof"] = latest_block_date.isoformat()
    combined["status"] = "ok" if all(dates.values()) else "partial"
    combined["block_asof"] = {key: _iso(dates[key]) for key in BLOCK_KEYS}
    combined["freshness"] = metadata
    combined["nok_residual"] = residual_diagnostics
    combined["method_note_freshness"] = (
        "Each operational block is evaluated at its own latest complete input date. "
        "No score equation, weight or threshold in the v0.4.1 core is changed."
    )
    return combined


__all__ = [
    "BLOCK_KEYS",
    "FRESHNESS_LABELS",
    "block_asof_dates",
    "evaluate_fresh_regimes",
    "previous_block_dates",
]
