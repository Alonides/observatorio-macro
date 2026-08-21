"""Motor de estado estructural, deliberadamente separado del motor de acto."""

from __future__ import annotations

from .methodology import load_methodology, manifest


METHODOLOGY = load_methodology()


def _latest_point(points: list[dict]) -> dict | None:
    return points[-1] if points else None


def _dimension(key: str, title: str, status: str, value=None, unit=None, **details) -> dict:
    return {
        "key": key,
        "title": title,
        "status": status,
        "value": value,
        "unit": unit,
        **details,
    }


def _percentile(values: list[float], current: float) -> float | None:
    if not values:
        return None
    return round(sum(value <= current for value in values) / len(values) * 100, 1)


def evaluate_state(series: dict[str, list[dict]]) -> dict:
    real_points = series.get("DFII10", [])
    real_latest = _latest_point(real_points)
    real_values = [float(point["value"]) for point in real_points if point.get("value") is not None]
    real_start = real_points[0]["date"] if real_points else None
    real_coverage = "full_since_2003" if real_start and real_start <= "2003-12-31" else "partial_history"

    public_debt = _latest_point(series.get("US_DEBT_HELD_PUBLIC", []))
    gross_debt = _latest_point(series.get("GFDEBTN", []))
    gdp = _latest_point(series.get("GDP", []))
    interest = _latest_point(series.get("A091RC1Q027SBEA", []))

    public_ratio = None
    gross_ratio = None
    interest_ratio = None
    if gdp and gdp.get("value"):
        if public_debt:
            public_ratio = float(public_debt["value"]) / (float(gdp["value"]) * 1000) * 100
        if gross_debt:
            gross_ratio = float(gross_debt["value"]) / (float(gdp["value"]) * 1000) * 100
        if interest:
            interest_ratio = float(interest["value"]) / float(gdp["value"]) * 100

    dimensions = [
        _dimension(
            "real_yield_level",
            "Nivel del rendimiento real a 10 años",
            "available" if real_latest else "missing",
            None if real_latest is None else real_latest["value"],
            "% real",
            percentile_available_sample=(
                None if real_latest is None else _percentile(real_values, float(real_latest["value"]))
            ),
            sample_start=real_start,
            sample_end=None if real_latest is None else real_latest["date"],
            coverage_status=real_coverage,
            note="El percentil no se considera historico completo hasta cubrir 2003-presente.",
        ),
        _dimension(
            "debt_held_by_public_to_gdp",
            "Deuda en manos del publico / PIB",
            "available" if public_ratio is not None else "missing",
            None if public_ratio is None else round(public_ratio, 1),
            "%",
            numerator_date=None if public_debt is None else public_debt["date"],
            denominator_date=None if gdp is None else gdp["date"],
            gross_debt_context_pct=None if gross_ratio is None else round(gross_ratio, 1),
        ),
        _dimension(
            "interest_burden",
            "Intereses federales / PIB",
            "available" if interest_ratio is not None else "missing",
            None if interest_ratio is None else round(interest_ratio, 2),
            "%",
            numerator_date=None if interest is None else interest["date"],
            denominator_date=None if gdp is None else gdp["date"],
        ),
        _dimension(
            "bill_share_of_marketable_debt",
            "Letras / deuda negociable",
            "pending_data",
            unit="%",
            note="Pendiente de Monthly Statement of the Public Debt.",
        ),
        _dimension(
            "foreign_official_holdings_trend",
            "Tenencias oficiales extranjeras",
            "pending_data",
            unit="% interanual",
            note="Pendiente de integrar Treasury International Capital.",
        ),
        _dimension(
            "dollar_reserve_share",
            "Cuota del dolar en reservas mundiales",
            "pending_data",
            unit="%",
            note="Pendiente de integrar COFER del FMI.",
        ),
    ]

    return {
        "engine": "structural_state",
        "aggregate_score": None,
        "aggregate_label": None,
        "methodology": manifest(METHODOLOGY),
        "dimensions": dimensions,
        "note": "Vector estructural independiente: sus dimensiones no se suman al motor H0/H1/H2.",
    }
