"""Synthetic falsification scenarios for model v0.3."""

from __future__ import annotations

from datetime import date, timedelta

from .regime import evaluate_regimes


def _days(count: int, start: date = date(2026, 1, 1)) -> list[str]:
    return [(start + timedelta(days=index)).isoformat() for index in range(count)]


def _shock(base: float, delta: float, count: int = 100, shock_sessions: int = 20) -> list[float]:
    values = [base] * (count - shock_sessions - 1)
    values.extend(base + delta * step / shock_sessions for step in range(shock_sessions + 1))
    return values


def _path(anchors: list[tuple[int, float]], count: int = 100) -> list[float]:
    """Piecewise-linear path through inclusive index/value anchors."""
    if not anchors or anchors[0][0] != 0 or anchors[-1][0] != count - 1:
        raise ValueError("anchors must cover index 0 through count - 1")
    values = [0.0] * count
    for (left_i, left_v), (right_i, right_v) in zip(anchors, anchors[1:]):
        span = right_i - left_i
        for offset in range(span + 1):
            values[left_i + offset] = left_v + (right_v - left_v) * offset / span
    return values


def _series(values: list[float], days: list[str]) -> list[dict]:
    return [{"date": day, "value": value} for day, value in zip(days, values)]


def _base(count: int = 100) -> dict[str, list[dict]]:
    days = _days(count)
    return {
        "DGS10": _series([4.0] * count, days),
        "DGS30": _series([4.2] * count, days),
        "DFII10": _series([2.0] * count, days),
        "DTWEXBGS": _series([100.0] * count, days),
        "VIXCLS": _series([18.0] * count, days),
        "GOLDAMGBD228NLBM": _series([2500.0] * count, days),
        "DCOILBRENTEU": _series([80.0] * count, days),
        "DEXUSEU": _series([1.0] * count, days),
        "DEXNOUS": _series([10.0] * count, days),
        "DEXSDUS": _series([10.0] * count, days),
        "IRLTLT01DEM156N": _series([3.0] * count, days),
        "IRLTLT01NOM156N": _series([4.0] * count, days),
    }


def duration_shock() -> dict:
    data = _base()
    days = _days(100)
    data["DGS30"] = _series(_shock(4.2, 0.60), days)
    data["DGS10"] = _series(_shock(4.0, 0.55), days)
    data["IRLTLT01DEM156N"] = _series(_shock(3.0, 0.55), days)
    data["DTWEXBGS"] = _series(_shock(100.0, 5.0), days)
    data["VIXCLS"] = _series(_shock(18.0, 17.0), days)
    return data


def us_rejection() -> dict:
    data = _base()
    days = _days(100)
    data["DGS30"] = _series(_shock(4.2, 0.60, shock_sessions=10), days)
    data["DGS10"] = _series(_shock(4.0, 0.55, shock_sessions=10), days)
    data["DTWEXBGS"] = _series(_shock(100.0, -5.0, shock_sessions=10), days)
    data["VIXCLS"] = _series(_shock(18.0, 27.0, shock_sessions=10), days)
    data["GOLDAMGBD228NLBM"] = _series(_shock(2500.0, 300.0), days)
    data["DFII10"] = _series(_shock(2.0, 0.25), days)
    return data


def us_rejection_regime() -> dict:
    """Persistent US-specific rejection with structural confirmation."""
    data = _base()
    days = _days(100)
    data["DGS30"] = _series(_shock(4.2, 0.80, shock_sessions=20), days)
    data["DGS10"] = _series(_shock(4.0, 0.70, shock_sessions=20), days)
    data["DTWEXBGS"] = _series(_shock(100.0, -8.0, shock_sessions=20), days)
    data["VIXCLS"] = _series(_shock(18.0, 42.0, shock_sessions=20), days)
    data["GOLDAMGBD228NLBM"] = _series(_shock(2500.0, 450.0, shock_sessions=20), days)
    data["DFII10"] = _series(_shock(2.0, 0.35, shock_sessions=20), days)
    return data


def dollar_shortage() -> dict:
    data = _base()
    days = _days(100)
    data["DGS30"] = _series(_shock(4.2, -0.50, shock_sessions=10), days)
    data["DGS10"] = _series(_shock(4.0, -0.45, shock_sessions=10), days)
    data["DTWEXBGS"] = _series(_shock(100.0, 8.0, shock_sessions=10), days)
    data["VIXCLS"] = _series(_shock(18.0, 47.0, shock_sessions=10), days)
    return data


def nok_stress() -> dict:
    data = _base()
    days = _days(100)
    data["DEXNOUS"] = _series(_shock(10.0, 1.2), days)
    data["DEXSDUS"] = _series(_shock(10.0, 0.2), days)
    data["IRLTLT01NOM156N"] = _series(_shock(4.0, 0.50), days)
    return data


def false_usdnok_reversal() -> dict:
    """USD/NOK falls, but EUR/NOK and NOK/SEK do not improve."""
    data = _base()
    days = _days(100)
    data["DEXNOUS"] = _series(_path([(0, 10.0), (59, 10.0), (79, 12.0), (99, 11.4)]), days)
    data["DEXUSEU"] = _series(_path([(0, 1.0), (79, 1.0), (99, 12.0 / 11.4)]), days)
    data["DEXSDUS"] = _series(_path([(0, 10.0), (79, 10.0), (99, 9.5)]), days)
    data["IRLTLT01NOM156N"] = _series([4.0] * 100, days)
    return data


def norwegian_reversal_candidate() -> dict:
    data = _base()
    days = _days(100)
    data["DEXNOUS"] = _series(_path([(0, 10.0), (59, 10.0), (79, 12.0), (99, 11.3)]), days)
    data["DEXSDUS"] = _series(_path([(0, 10.0), (59, 10.0), (79, 10.4), (99, 10.35)]), days)
    data["DEXUSEU"] = _series([1.0] * 100, days)
    data["IRLTLT01NOM156N"] = _series([4.0] * 100, days)
    data["DCOILBRENTEU"] = _series(_path([(0, 80.0), (79, 80.0), (99, 82.0)]), days)
    return data


def norwegian_reversal_confirmed() -> dict:
    data = norwegian_reversal_candidate()
    days = _days(100)
    data["NOK_RESIDUAL_Z20"] = _series(
        _path([(0, 0.0), (59, 0.0), (79, 3.0), (99, -1.5)]),
        days,
    )
    return data


def synthetic_results() -> dict:
    scenarios = {
        "duration_shock": duration_shock(),
        "us_rejection": us_rejection(),
        "us_rejection_regime": us_rejection_regime(),
        "dollar_shortage": dollar_shortage(),
        "nok_stress": nok_stress(),
        "false_usdnok_reversal": false_usdnok_reversal(),
        "norwegian_reversal_candidate": norwegian_reversal_candidate(),
        "norwegian_reversal_confirmed": norwegian_reversal_confirmed(),
    }
    return {name: evaluate_regimes(data) for name, data in scenarios.items()}


__all__ = [
    "duration_shock",
    "us_rejection",
    "us_rejection_regime",
    "dollar_shortage",
    "nok_stress",
    "false_usdnok_reversal",
    "norwegian_reversal_candidate",
    "norwegian_reversal_confirmed",
    "synthetic_results",
]
