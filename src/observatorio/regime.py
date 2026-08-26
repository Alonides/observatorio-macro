"""Debt and NOK regime classifier, specification v0.3.

The module is deliberately deterministic and dependency-free. It separates:

* URP: a short US rejection pulse;
* URR: persistence of that pulse into a rejection regime;
* DSS: dollar shortage stress;
* NKS: stress specific to NOK;
* NRS: a possible Norwegian reversal after a NOK shock.

No missing component is silently treated as zero. Composite scores are
renormalised over the components that are actually available and report their
coverage. A low residual never proves the null hypothesis; it simply does not
activate that signal.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from datetime import date
from math import isfinite
from statistics import median
from typing import Iterable, Mapping, Sequence


MODEL_VERSION = "0.3.0"

PARAMETERS = {
    "windows": {"pulse": 10, "confirm": 20, "structural": 60},
    "urp": {
        "yield_bp": (20.0, 35.0, 50.0),
        "usd_drop_pct": (1.0, 2.0, 4.0),
        "spx_drop_pct": (3.0, 7.0, 12.0),
        "vix_level": (25.0, 40.0, 60.0),
        "us_bund_widening_bp": (10.0, 25.0, 50.0),
        "weights": {"yield": 0.35, "usd": 0.30, "risk": 0.20, "relative": 0.15},
        "unconfirmed_cap": 59.0,
    },
    "urr": {
        "pulse_min": 50.0,
        "pulse_days_last_3": 2,
        "discrimination_days_last_10": 5,
        "regime_days_last_20": 10,
        "usd_drop_20_pct": 4.0,
        "usd_drop_60_pct": 7.0,
        "gold_rise_20_pct": 5.0,
        "real_yield_rise_20_bp": 10.0,
    },
    "dss": {
        "usd_rise_10_pct": (2.0, 4.0, 8.0),
        "usd_rise_20_pct": (4.0, 6.0, 10.0),
        "vix_level": (25.0, 40.0, 60.0),
    },
    "nks": {
        "eurnok_rise_20_pct": (3.0, 6.0, 10.0),
        "noksek_rise_20_pct": (1.5, 3.0, 6.0),
        "residual_z20": (1.5, 2.5, 3.5),
        "no_bund_widening_20_bp": (15.0, 30.0, 60.0),
        "nibor_ois_widening_20_bp": (15.0, 30.0, 60.0),
        "weights": {"eurnok": 0.35, "residual": 0.25, "noksek": 0.20, "funding": 0.20},
    },
    "nrs": {
        "prior_nks_min": 65.0,
        "eurnok_recovery_pct": -3.0,
        "noksek_recovery_pct": -2.0,
        "residual_z_max": -1.0,
        "no_bund_baseline_buffer_bp": 10.0,
        "brent_floor_from_peak_pct": -10.0,
    },
}


@dataclass(frozen=True)
class SeriesView:
    """Sorted, numeric observations with as-of and session-lag access."""

    dates: tuple[date, ...]
    values: tuple[float, ...]

    @classmethod
    def from_points(cls, points: Iterable[Mapping[str, object]]) -> "SeriesView":
        by_day: dict[date, float] = {}
        for point in points:
            raw_day = point.get("date")
            raw_value = point.get("value")
            if raw_day is None or raw_value is None:
                continue
            try:
                day = raw_day if isinstance(raw_day, date) else date.fromisoformat(str(raw_day))
                value = float(raw_value)
            except (TypeError, ValueError):
                continue
            if isfinite(value):
                by_day[day] = value
        ordered = sorted(by_day.items())
        return cls(tuple(day for day, _ in ordered), tuple(value for _, value in ordered))

    def __bool__(self) -> bool:
        return bool(self.dates)

    def position(self, asof: date | None = None) -> int | None:
        if not self.dates:
            return None
        if asof is None:
            return len(self.dates) - 1
        index = bisect_right(self.dates, asof) - 1
        return index if index >= 0 else None

    def value(self, asof: date | None = None) -> float | None:
        index = self.position(asof)
        return None if index is None else self.values[index]

    def day(self, asof: date | None = None) -> date | None:
        index = self.position(asof)
        return None if index is None else self.dates[index]

    def lag_value(self, sessions: int, asof: date | None = None) -> float | None:
        if sessions < 0:
            raise ValueError("sessions must be non-negative")
        index = self.position(asof)
        if index is None or index - sessions < 0:
            return None
        return self.values[index - sessions]

    def change(self, sessions: int, asof: date | None = None) -> float | None:
        current = self.value(asof)
        prior = self.lag_value(sessions, asof)
        if current is None or prior is None:
            return None
        return current - prior

    def pct_change(self, sessions: int, asof: date | None = None) -> float | None:
        current = self.value(asof)
        prior = self.lag_value(sessions, asof)
        if current is None or prior in {None, 0.0}:
            return None
        return (current / prior - 1.0) * 100.0

    def last_dates(self, count: int, asof: date | None = None) -> tuple[date, ...]:
        index = self.position(asof)
        if index is None or count <= 0:
            return ()
        start = max(0, index - count + 1)
        return self.dates[start:index + 1]


class MarketData:
    """Cached raw and derived market series."""

    def __init__(self, series: Mapping[str, Sequence[Mapping[str, object]]]):
        self._raw = series
        self._cache: dict[str, SeriesView] = {}

    def view(self, series_id: str) -> SeriesView:
        if series_id not in self._cache:
            self._cache[series_id] = SeriesView.from_points(self._raw.get(series_id, ()))
        return self._cache[series_id]

    def product(self, key: str, left_id: str, right_id: str) -> SeriesView:
        if key not in self._cache:
            self._cache[key] = _combine_exact(self.view(left_id), self.view(right_id), lambda a, b: a * b)
        return self._cache[key]

    def ratio(self, key: str, numerator_id: str, denominator_id: str) -> SeriesView:
        if key not in self._cache:
            self._cache[key] = _combine_exact(
                self.view(numerator_id), self.view(denominator_id),
                lambda a, b: a / b if b else float("nan"),
            )
        return self._cache[key]

    def difference(self, key: str, left_id: str, right_id: str) -> SeriesView:
        if key not in self._cache:
            self._cache[key] = _combine_asof(self.view(left_id), self.view(right_id), lambda a, b: a - b)
        return self._cache[key]

    def eurnok(self) -> SeriesView:
        return self.product("__EURNOK", "DEXNOUS", "DEXUSEU")

    def noksek(self) -> SeriesView:
        return self.ratio("__NOKSEK", "DEXNOUS", "DEXSDUS")

    def us_bund(self) -> SeriesView:
        return self.difference("__US_BUND", "DGS10", "IRLTLT01DEM156N")

    def no_bund(self) -> SeriesView:
        return self.difference("__NO_BUND", "IRLTLT01NOM156N", "IRLTLT01DEM156N")


def _combine_exact(left: SeriesView, right: SeriesView, operation) -> SeriesView:
    left_map = dict(zip(left.dates, left.values))
    right_map = dict(zip(right.dates, right.values))
    points = []
    for day in sorted(left_map.keys() & right_map.keys()):
        value = operation(left_map[day], right_map[day])
        if isfinite(value):
            points.append({"date": day, "value": value})
    return SeriesView.from_points(points)


def _combine_asof(left: SeriesView, right: SeriesView, operation) -> SeriesView:
    points = []
    for day, left_value in zip(left.dates, left.values):
        right_value = right.value(day)
        if right_value is None:
            continue
        value = operation(left_value, right_value)
        if isfinite(value):
            points.append({"date": day, "value": value})
    return SeriesView.from_points(points)


def _score_up(value: float | None, thresholds: Sequence[float]) -> float | None:
    if value is None:
        return None
    t1, t2, t3 = (float(item) for item in thresholds)
    if not 0 < t1 < t2 < t3:
        raise ValueError("thresholds must be strictly increasing and positive")
    if value <= 0:
        return 0.0
    knots = ((0.0, 0.0), (t1, 33.0), (t2, 67.0), (t3, 100.0))
    for (x0, y0), (x1, y1) in zip(knots, knots[1:]):
        if value <= x1:
            return y0 + (value - x0) / (x1 - x0) * (y1 - y0)
    return 100.0


def _weighted_available(components: Mapping[str, float | None], weights: Mapping[str, float]) -> tuple[float | None, float]:
    available = [(name, value) for name, value in components.items() if value is not None and name in weights]
    available_weight = sum(weights[name] for name, _ in available)
    if not available or available_weight <= 0:
        return None, 0.0
    score = sum(weights[name] * float(value) for name, value in available) / available_weight
    return max(0.0, min(100.0, score)), available_weight / sum(weights.values())


def _risk_block(md: MarketData, asof: date) -> dict:
    spx_decline = None
    if md.view("SP500").dates:
        change = md.view("SP500").pct_change(10, asof)
        spx_decline = None if change is None else -change
    vix = md.view("VIXCLS").value(asof)
    spx_score = _score_up(spx_decline, PARAMETERS["urp"]["spx_drop_pct"])
    vix_score = _score_up(vix, PARAMETERS["urp"]["vix_level"])
    scores = [score for score in (spx_score, vix_score) if score is not None]
    score = max(scores) if scores else None
    gate = ((spx_decline is not None and spx_decline >= 3.0) or (vix is not None and vix >= 25.0))
    return {
        "score": score,
        "gate": gate,
        "sp500_decline_10_pct": spx_decline,
        "vix": vix,
        "method": "max(SP500 decline score, VIX level score); no double counting",
    }


def _urp_at(md: MarketData, asof: date) -> dict:
    yield_change = md.view("DGS30").change(10, asof)
    yield_bp = None if yield_change is None else yield_change * 100.0
    usd_change = md.view("DTWEXBGS").pct_change(10, asof)
    usd_drop = None if usd_change is None else -usd_change
    relative_change = md.us_bund().change(10, asof)
    relative_bp = None if relative_change is None else relative_change * 100.0
    risk = _risk_block(md, asof)

    core_complete = yield_bp is not None and usd_drop is not None and risk["score"] is not None
    gate = bool(core_complete and yield_bp >= 20.0 and usd_drop >= 1.0 and risk["gate"])
    components = {
        "yield": _score_up(yield_bp, PARAMETERS["urp"]["yield_bp"]),
        "usd": _score_up(usd_drop, PARAMETERS["urp"]["usd_drop_pct"]),
        "risk": risk["score"],
        "relative": _score_up(relative_bp, PARAMETERS["urp"]["us_bund_widening_bp"]),
    }
    raw_score, coverage = _weighted_available(components, PARAMETERS["urp"]["weights"])
    relative_confirmed = relative_bp is not None and relative_bp >= 10.0
    if not core_complete:
        score = None
        state = "insufficient_data"
    elif not gate:
        score = 0.0
        state = "inactive"
    else:
        score = raw_score or 0.0
        if not relative_confirmed:
            score = min(score, PARAMETERS["urp"]["unconfirmed_cap"])
        state = "confirmed_pulse" if relative_confirmed and score >= 50 else "unconfirmed_pulse"

    return {
        "asof": asof.isoformat(),
        "score": None if score is None else round(score, 2),
        "state": state,
        "gate": gate,
        "relative_confirmed": relative_confirmed,
        "coverage": round(coverage, 3),
        "values": {
            "ust30_change_10_bp": yield_bp,
            "broad_usd_drop_10_pct": usd_drop,
            "us10_bund10_spread_change_10_bp": relative_bp,
            **{key: value for key, value in risk.items() if key != "score"},
        },
        "component_scores": components,
    }


def _urp_history(md: MarketData, asof: date, sessions: int = 20) -> list[dict]:
    reference = md.view("DGS30")
    return [_urp_at(md, day) for day in reference.last_dates(sessions, asof)]


def _evaluate_urr(md: MarketData, asof: date) -> dict:
    history = _urp_history(md, asof, 20)
    scores = [item["score"] for item in history]
    last3 = scores[-3:]
    last10 = scores[-10:]
    last20 = scores[-20:]
    pulse_count = sum(score is not None and score >= 50.0 for score in last3)
    discrimination_count = sum(score is not None and score >= 50.0 for score in last10)
    regime_count = sum(score is not None and score >= 50.0 for score in last20)
    relative_confirmation = any(
        item["relative_confirmed"] and item["score"] is not None and item["score"] >= 50.0
        for item in history[-10:]
    )

    usd20 = md.view("DTWEXBGS").pct_change(20, asof)
    usd60 = md.view("DTWEXBGS").pct_change(60, asof)
    usd_drop20 = None if usd20 is None else -usd20
    usd_drop60 = None if usd60 is None else -usd60
    gold20 = md.view("GOLDAMGBD228NLBM").pct_change(20, asof)
    real20 = md.view("DFII10").change(20, asof)
    real20_bp = None if real20 is None else real20 * 100.0
    structural_confirmation = bool(
        gold20 is not None
        and real20_bp is not None
        and gold20 >= PARAMETERS["urr"]["gold_rise_20_pct"]
        and real20_bp >= PARAMETERS["urr"]["real_yield_rise_20_bp"]
    )
    usd_regime_gate = bool(
        (usd_drop20 is not None and usd_drop20 >= PARAMETERS["urr"]["usd_drop_20_pct"])
        or (usd_drop60 is not None and usd_drop60 >= PARAMETERS["urr"]["usd_drop_60_pct"])
    )

    pulse = pulse_count >= PARAMETERS["urr"]["pulse_days_last_3"]
    discrimination = bool(
        discrimination_count >= PARAMETERS["urr"]["discrimination_days_last_10"]
        and relative_confirmation
    )
    rejection_regime = bool(
        regime_count >= PARAMETERS["urr"]["regime_days_last_20"]
        and relative_confirmation
        and usd_regime_gate
        and structural_confirmation
    )
    if rejection_regime:
        state = "rejection_regime"
    elif discrimination:
        state = "us_discrimination"
    elif pulse:
        state = "rejection_pulse"
    else:
        state = "inactive"

    return {
        "state": state,
        "pulse": pulse,
        "discrimination": discrimination,
        "rejection_regime": rejection_regime,
        "counts": {
            "urp_ge_50_last_3": pulse_count,
            "urp_ge_50_last_10": discrimination_count,
            "urp_ge_50_last_20": regime_count,
        },
        "confirmations": {
            "relative": relative_confirmation,
            "usd_persistence": usd_regime_gate,
            "gold_up_with_real_yield_up": structural_confirmation,
        },
        "values": {
            "broad_usd_drop_20_pct": usd_drop20,
            "broad_usd_drop_60_pct": usd_drop60,
            "gold_change_20_pct": gold20,
            "real_yield_change_20_bp": real20_bp,
        },
    }


def _dss_at(md: MarketData, asof: date) -> dict:
    usd10 = md.view("DTWEXBGS").pct_change(10, asof)
    usd20 = md.view("DTWEXBGS").pct_change(20, asof)
    vix = md.view("VIXCLS").value(asof)
    score10 = _score_up(usd10, PARAMETERS["dss"]["usd_rise_10_pct"])
    score20 = _score_up(usd20, PARAMETERS["dss"]["usd_rise_20_pct"])
    vix_score = _score_up(vix, PARAMETERS["dss"]["vix_level"])

    window_score, window_coverage = _weighted_available(
        {"usd10": score10, "usd20": score20}, {"usd10": 0.60, "usd20": 0.40}
    )
    final_score, coverage = _weighted_available(
        {"usd": window_score, "risk": vix_score}, {"usd": 0.65, "risk": 0.35}
    )
    gate = bool(
        ((usd10 is not None and usd10 >= 2.0) or (usd20 is not None and usd20 >= 4.0))
        and vix is not None
        and vix >= 25.0
    )
    yield_change = md.view("DGS30").change(10, asof)
    yield_bp = None if yield_change is None else yield_change * 100.0
    if not gate:
        state = "inactive" if final_score is not None else "insufficient_data"
        score = 0.0 if final_score is not None else None
    elif yield_bp is None:
        state = "dollar_shortage_unclassified"
        score = final_score
    elif yield_bp <= 0:
        state = "traditional_safe_haven"
        score = final_score
    else:
        state = "dollar_shortage_with_treasury_dislocation"
        score = final_score
    return {
        "asof": asof.isoformat(),
        "score": None if score is None else round(score, 2),
        "state": state,
        "gate": gate,
        "coverage": round(coverage * window_coverage, 3),
        "values": {
            "broad_usd_rise_10_pct": usd10,
            "broad_usd_rise_20_pct": usd20,
            "vix": vix,
            "ust30_change_10_bp": yield_bp,
        },
    }


def _nks_at(md: MarketData, asof: date) -> dict:
    eurnok_change = md.eurnok().pct_change(20, asof)
    noksek_change = md.noksek().pct_change(20, asof)
    residual_z = md.view("NOK_RESIDUAL_Z20").value(asof)
    no_bund_change = md.no_bund().change(20, asof)
    no_bund_bp = None if no_bund_change is None else no_bund_change * 100.0
    nibor_change = md.view("NIBOR_OIS").change(20, asof)
    nibor_bp = None if nibor_change is None else nibor_change * 100.0

    no_bund_score = _score_up(no_bund_bp, PARAMETERS["nks"]["no_bund_widening_20_bp"])
    nibor_score = _score_up(nibor_bp, PARAMETERS["nks"]["nibor_ois_widening_20_bp"])
    funding_scores = [value for value in (no_bund_score, nibor_score) if value is not None]
    funding_score = max(funding_scores) if funding_scores else None

    components = {
        "eurnok": _score_up(eurnok_change, PARAMETERS["nks"]["eurnok_rise_20_pct"]),
        "residual": _score_up(residual_z, PARAMETERS["nks"]["residual_z20"]),
        "noksek": _score_up(noksek_change, PARAMETERS["nks"]["noksek_rise_20_pct"]),
        "funding": funding_score,
    }
    score, coverage = _weighted_available(components, PARAMETERS["nks"]["weights"])
    if score is None or eurnok_change is None:
        state = "insufficient_data"
    elif score >= 65.0:
        state = "severe"
    elif score >= 50.0:
        state = "stress"
    elif score >= 35.0:
        state = "watch"
    else:
        state = "normal"
    return {
        "asof": asof.isoformat(),
        "score": None if score is None else round(score, 2),
        "state": state,
        "coverage": round(coverage, 3),
        "values": {
            "eurnok_change_20_pct": eurnok_change,
            "noksek_change_20_pct": noksek_change,
            "nok_residual_z20": residual_z,
            "norway_bund_change_20_bp": no_bund_bp,
            "nibor_ois_change_20_bp": nibor_bp,
        },
        "component_scores": components,
        "note": "Brent and VIX are not added again when a residual series is supplied; doing so would double count them.",
    }


def _nks_history(md: MarketData, asof: date, sessions: int = 60) -> list[dict]:
    reference = md.eurnok()
    return [_nks_at(md, day) for day in reference.last_dates(sessions, asof)]


def _nrs_at(md: MarketData, asof: date) -> dict:
    history = _nks_history(md, asof, 60)
    scored = [(item["asof"], item["score"]) for item in history if item["score"] is not None]
    if not scored:
        return {"asof": asof.isoformat(), "score": None, "state": "insufficient_data", "gates": {}}
    peak_nks_day_raw, max_nks = max(scored, key=lambda item: item[1])
    peak_nks_day = date.fromisoformat(peak_nks_day_raw)
    prior_stress = max_nks >= PARAMETERS["nrs"]["prior_nks_min"]

    eurnok = md.eurnok()
    noksek = md.noksek()
    last60_dates = eurnok.last_dates(60, asof)
    if not last60_dates:
        return {"asof": asof.isoformat(), "score": None, "state": "insufficient_data", "gates": {}}
    window_start = last60_dates[0]
    eurnok_pairs = [(day, value) for day, value in zip(eurnok.dates, eurnok.values) if window_start <= day <= asof]
    noksek_pairs = [(day, value) for day, value in zip(noksek.dates, noksek.values) if window_start <= day <= asof]
    eurnok_peak_day, eurnok_peak = max(eurnok_pairs, key=lambda item: item[1]) if eurnok_pairs else (None, None)
    noksek_peak_day, noksek_peak = max(noksek_pairs, key=lambda item: item[1]) if noksek_pairs else (None, None)
    eurnok_now = eurnok.value(asof)
    noksek_now = noksek.value(asof)
    eurnok_recovery = None if eurnok_peak in {None, 0.0} or eurnok_now is None else (eurnok_now / eurnok_peak - 1.0) * 100.0
    noksek_recovery = None if noksek_peak in {None, 0.0} or noksek_now is None else (noksek_now / noksek_peak - 1.0) * 100.0

    no_bund = md.no_bund()
    baseline_dates = no_bund.last_dates(60, asof)[:20]
    baseline_values = [no_bund.value(day) for day in baseline_dates]
    baseline_values = [value for value in baseline_values if value is not None]
    no_bund_baseline = median(baseline_values) if baseline_values else None
    no_bund_now = no_bund.value(asof)
    no_bund_ok = bool(
        no_bund_baseline is not None
        and no_bund_now is not None
        and (no_bund_now - no_bund_baseline) * 100.0 <= PARAMETERS["nrs"]["no_bund_baseline_buffer_bp"]
    )

    brent = md.view("DCOILBRENTEU")
    brent_peak_day = eurnok_peak_day or peak_nks_day
    brent_at_peak = brent.value(brent_peak_day)
    brent_now = brent.value(asof)
    brent_change = None if brent_at_peak in {None, 0.0} or brent_now is None else (brent_now / brent_at_peak - 1.0) * 100.0
    brent_ok = brent_change is not None and brent_change >= PARAMETERS["nrs"]["brent_floor_from_peak_pct"]

    residual = md.view("NOK_RESIDUAL_Z20").value(asof)
    residual_ok = residual is not None and residual <= PARAMETERS["nrs"]["residual_z_max"]
    eurnok_ok = eurnok_recovery is not None and eurnok_recovery <= PARAMETERS["nrs"]["eurnok_recovery_pct"]
    noksek_ok = noksek_recovery is not None and noksek_recovery <= PARAMETERS["nrs"]["noksek_recovery_pct"]

    gates = {
        "prior_nks_stress": prior_stress,
        "eurnok_recovery": eurnok_ok,
        "noksek_recovery": noksek_ok,
        "norway_bund_normalised": no_bund_ok,
        "brent_not_falling_further": brent_ok,
        "negative_nok_residual": residual_ok if residual is not None else None,
    }
    observable = {key: value for key, value in gates.items() if value is not None}
    score = sum(bool(value) for value in observable.values()) / len(observable) * 100.0 if observable else None
    observable_candidate = all(gates[key] is True for key in (
        "prior_nks_stress", "eurnok_recovery", "noksek_recovery",
        "norway_bund_normalised", "brent_not_falling_further",
    ))
    if not prior_stress:
        state = "inactive"
    elif observable_candidate and residual is None:
        state = "candidate_unconfirmed_residual_missing"
    elif observable_candidate and residual_ok:
        state = "confirmed"
    else:
        state = "inactive"

    return {
        "asof": asof.isoformat(),
        "score": None if score is None else round(score, 2),
        "state": state,
        "prior_nks_max_60": round(max_nks, 2),
        "prior_nks_peak_date": peak_nks_day.isoformat(),
        "gates": gates,
        "values": {
            "eurnok_recovery_from_60d_peak_pct": eurnok_recovery,
            "eurnok_peak_date": eurnok_peak_day.isoformat() if eurnok_peak_day else None,
            "noksek_recovery_from_60d_peak_pct": noksek_recovery,
            "noksek_peak_date": noksek_peak_day.isoformat() if noksek_peak_day else None,
            "norway_bund_baseline_pct_points": no_bund_baseline,
            "norway_bund_current_pct_points": no_bund_now,
            "brent_change_since_eurnok_peak_pct": brent_change,
            "nok_residual_z20": residual,
        },
        "note": "USD/NOK is deliberately excluded from the reversal gate.",
    }


def _latest_common_asof(md: MarketData) -> date | None:
    preferred = ("DGS30", "DTWEXBGS", "DEXNOUS")
    days = [md.view(series_id).day() for series_id in preferred if md.view(series_id).day() is not None]
    return min(days) if days else None


def evaluate_regimes(
    series: Mapping[str, Sequence[Mapping[str, object]]],
    asof: str | date | None = None,
) -> dict:
    """Evaluate all v0.3 blocks at one date.

    The existing H0/H1/H2 engine remains untouched. This function is an
    experimental companion until continuous out-of-sample validation is done.
    """
    md = MarketData(series)
    if asof is None:
        day = _latest_common_asof(md)
    elif isinstance(asof, date):
        day = asof
    else:
        day = date.fromisoformat(asof)
    if day is None:
        return {
            "model_version": MODEL_VERSION,
            "asof": None,
            "status": "insufficient_data",
            "urp": None,
            "urr": None,
            "dss": None,
            "nks": None,
            "nrs": None,
        }

    urp = _urp_at(md, day)
    urr = _evaluate_urr(md, day)
    dss = _dss_at(md, day)
    nks = _nks_at(md, day)
    nrs = _nrs_at(md, day)
    required = {
        "urp_core": all(md.view(item).dates for item in ("DGS30", "DTWEXBGS", "VIXCLS")),
        "relative_us": all(md.view(item).dates for item in ("DGS10", "IRLTLT01DEM156N")),
        "nok_core": all(md.view(item).dates for item in ("DEXNOUS", "DEXUSEU", "DEXSDUS")),
        "norway_funding": all(md.view(item).dates for item in ("IRLTLT01NOM156N", "IRLTLT01DEM156N")),
        "nok_residual": bool(md.view("NOK_RESIDUAL_Z20").dates),
        "nibor_ois": bool(md.view("NIBOR_OIS").dates),
    }
    return {
        "model_version": MODEL_VERSION,
        "asof": day.isoformat(),
        "status": "ok" if required["urp_core"] and required["nok_core"] else "partial",
        "urp": urp,
        "urr": urr,
        "dss": dss,
        "nks": nks,
        "nrs": nrs,
        "data_coverage": required,
        "parameters": PARAMETERS,
        "method_note": (
            "URP and DSS are mutually diagnostic, not mutually exclusive scores. "
            "NRS is only confirmed when the NOK residual is available and negative."
        ),
    }


__all__ = [
    "MODEL_VERSION",
    "PARAMETERS",
    "MarketData",
    "SeriesView",
    "evaluate_regimes",
]
