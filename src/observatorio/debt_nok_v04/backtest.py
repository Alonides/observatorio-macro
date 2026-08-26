"""Continuous v0.4.1 backtest with causal NOK residual and NRS history."""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Mapping, Sequence

# Importing the overlay first patches the falsified v0.3 risk gate.
from . import regime as _v4
from .residual import attach_nok_residual
from .. import backtest as _base

MODEL_VERSION = _v4.MODEL_VERSION
MIN_VALIDATED_NKS_COVERAGE = 0.75
MIN_PERSISTENT_NKS_SESSIONS = 2

NKS_EVENT_WINDOWS = {
    "lehman_2008": ("2008-09-12", "2009-01-31"),
    "oil_2014_15": ("2014-06-01", "2015-03-31"),
    "covid_2020": ("2020-02-19", "2020-04-30"),
    "inflation_2022": ("2022-04-01", "2022-10-31"),
    "banking_2023": ("2023-03-08", "2023-04-05"),
    "tariff_pulse_2025": ("2025-04-02", "2025-04-30"),
}

# Reversal is a post-shock phenomenon. Its validation windows must therefore
# extend beyond the stress windows used for NKS. The 60-session NRS memory is
# reflected in these deliberately wider, predeclared recovery windows.
NRS_RECOVERY_WINDOWS = {
    "lehman_recovery_2008_09": ("2008-10-10", "2009-06-30"),
    "oil_recovery_2014_15": ("2014-12-01", "2015-06-30"),
    "covid_recovery_2020": ("2020-03-20", "2020-06-30"),
    "inflation_recovery_2022": ("2022-09-26", "2023-01-31"),
    "banking_recovery_2023": ("2023-03-20", "2023-06-30"),
    "tariff_recovery_2025": ("2025-04-15", "2025-07-31"),
}


def _urr_rows(md: _v4.MarketData) -> list[dict]:
    rows: list[dict] = []
    mapping = {
        "inactive": 0.0,
        "rejection_pulse": 50.0,
        "us_discrimination": 75.0,
        "rejection_regime": 100.0,
    }
    for day in md.view("DGS30").dates:
        result = _v4._base._evaluate_urr(md, day)
        state = result.get("state")
        rows.append({
            "date": day.isoformat(),
            "score": mapping.get(state),
            "state": state,
        })
    return rows


def _nks_rows(md: _v4.MarketData) -> list[dict]:
    rows: list[dict] = []
    for day in md.eurnok().dates:
        result = _v4._base._nks_at(md, day)
        rows.append({
            "date": day.isoformat(),
            "score": result.get("score"),
            "state": result.get("state"),
            "coverage": result.get("coverage"),
        })
    return rows


def _validated_nks_rows(rows: list[dict]) -> list[dict]:
    output: list[dict] = []
    for row in rows:
        coverage = row.get("coverage")
        eligible = coverage is not None and coverage >= MIN_VALIDATED_NKS_COVERAGE
        output.append({
            **row,
            "score": row.get("score") if eligible else None,
            "state": row.get("state") if eligible else "insufficient_coverage",
            "validated": eligible,
        })
    return output


def _nrs_rows(md: _v4.MarketData) -> list[dict]:
    """Build NRS history without turning missing funding data into a negative.

    NRS explicitly requires the Norway-Bund gate. Norges Bank's homogeneous
    daily 10-year series begins in 2019, so earlier recovery windows are not
    valid negative controls. They are reported as unavailable instead.
    """
    rows: list[dict] = []
    mapping = {
        "inactive": 0.0,
        "candidate_unconfirmed_residual_missing": 50.0,
        "confirmed": 100.0,
    }
    no_bund = md.no_bund()
    brent = md.view("DCOILBRENTEU")
    for day in md.eurnok().dates:
        if no_bund.value(day) is None:
            rows.append({
                "date": day.isoformat(),
                "score": None,
                "state": "insufficient_funding_data",
            })
            continue
        if brent.value(day) is None:
            rows.append({
                "date": day.isoformat(),
                "score": None,
                "state": "insufficient_market_data",
            })
            continue
        result = _v4._base._nrs_at(md, day)
        state = result.get("state")
        rows.append({
            "date": day.isoformat(),
            "score": result.get("score") if state == "confirmed" else mapping.get(state),
            "state": state,
        })
    return rows


def _episodes(rows: list[dict], threshold: float = 50.0) -> list[dict]:
    episodes: list[dict] = []
    current: list[dict] = []
    for row in rows:
        score = row.get("score")
        if score is not None and score >= threshold:
            current.append(row)
        elif current:
            episodes.append(_summarise(current))
            current = []
    if current:
        episodes.append(_summarise(current))
    return episodes


def _summarise(rows: list[dict]) -> dict:
    peak = max(rows, key=lambda item: item["score"])
    return {
        "start": rows[0]["date"],
        "end": rows[-1]["date"],
        "sessions": len(rows),
        "peak_score": round(float(peak["score"]), 2),
        "peak_date": peak["date"],
        "peak_state": peak.get("state"),
    }


def _annual(rows: list[dict], threshold: float = 50.0) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        if row.get("score") is not None and row["score"] >= threshold:
            counts[row["date"][:4]] += 1
    return dict(sorted(counts.items()))


def _event_summary(
    rows: list[dict],
    windows: Mapping[str, tuple[str, str]] | None = None,
) -> dict:
    windows = windows or getattr(_base, "EVENT_WINDOWS", {})
    result: dict = {}
    for name, (start_raw, end_raw) in windows.items():
        start = date.fromisoformat(start_raw)
        end = date.fromisoformat(end_raw)
        selected = [
            row for row in rows
            if start <= date.fromisoformat(row["date"]) <= end
            and row.get("score") is not None
        ]
        if not selected:
            result[name] = {"available": False, "start": start_raw, "end": end_raw}
            continue
        peak = max(selected, key=lambda item: item["score"])
        result[name] = {
            "available": True,
            "start": start_raw,
            "end": end_raw,
            "observations": len(selected),
            "peak_score": round(float(peak["score"]), 2),
            "peak_date": peak["date"],
            "peak_state": peak.get("state"),
            "days_ge_50": sum(row["score"] >= 50.0 for row in selected),
            "confirmed_sessions": sum(row.get("state") == "confirmed" for row in selected),
        }
    return result


def _block(rows: list[dict], windows=None) -> dict:
    scored = [row for row in rows if row.get("score") is not None]
    return {
        "scored_sessions": len(scored),
        "episodes_ge_50": _episodes(rows),
        "annual_alert_sessions_ge_50": _annual(rows),
        "event_windows": _event_summary(rows, windows),
        "max_score": round(max((row["score"] for row in scored), default=0.0), 2),
    }


def run_continuous_backtest(
    series: Mapping[str, Sequence[Mapping[str, object]]],
    include_history: bool = False,
) -> dict:
    enriched, residual_diagnostics = attach_nok_residual(series)
    output = _base.run_continuous_backtest(enriched, include_history=include_history)
    output["model_version"] = MODEL_VERSION

    md = _v4.MarketData(enriched)
    urr_rows = _urr_rows(md)
    urr_block = _block(urr_rows)
    if include_history:
        urr_block["history"] = urr_rows
    output.setdefault("blocks", {})["urr"] = urr_block

    nks_rows = _nks_rows(md)
    validated_nks_rows = _validated_nks_rows(nks_rows)
    nks_block = _block(nks_rows, NKS_EVENT_WINDOWS)
    validated_episodes = _episodes(validated_nks_rows)
    nks_block.update({
        "minimum_validated_coverage": MIN_VALIDATED_NKS_COVERAGE,
        "validated_scored_sessions": sum(row.get("score") is not None for row in validated_nks_rows),
        "validated_episodes_ge_50": validated_episodes,
        "validated_annual_alert_sessions_ge_50": _annual(validated_nks_rows),
        "persistent_validated_episodes_ge_50": [
            episode for episode in validated_episodes
            if episode["sessions"] >= MIN_PERSISTENT_NKS_SESSIONS
        ],
        "minimum_persistent_sessions": MIN_PERSISTENT_NKS_SESSIONS,
        "validated_event_windows": _event_summary(validated_nks_rows, NKS_EVENT_WINDOWS),
        "interpretation_note": (
            "Raw NKS remains visible. Operational validation requires at least 75% "
            "component coverage; persistence is reported separately and does not "
            "change the frozen score or thresholds."
        ),
    })
    if include_history:
        nks_block["history"] = nks_rows
        nks_block["validated_history"] = validated_nks_rows
    output["blocks"]["nks"] = nks_block

    nrs_rows = _nrs_rows(md)
    nrs_block = _block(nrs_rows, NRS_RECOVERY_WINDOWS)
    nrs_block["confirmed_sessions"] = sum(row.get("state") == "confirmed" for row in nrs_rows)
    nrs_block["recovery_windows"] = nrs_block.pop("event_windows")
    nrs_block["interpretation_note"] = (
        "NRS is evaluated in post-shock recovery windows, not only inside the "
        "stress window that generated the preceding NKS episode. Windows without "
        "the required Norway-Bund history are unavailable, not negative results."
    )
    if include_history:
        nrs_block["history"] = nrs_rows
    output["blocks"]["nrs"] = nrs_block

    output["latest"] = _v4.evaluate_regimes(enriched)
    output["nok_residual"] = residual_diagnostics
    output["method_note_v041"] = (
        "The v0.4.1 continuous test attaches one walk-forward NOK residual "
        "before scoring all sessions. The residual, NKS and NRS therefore use "
        "the same causal history and are not recomputed with future data. Raw "
        "NKS scores are separated from coverage-validated and persistent alerts."
    )
    return output


__all__ = [
    "MIN_PERSISTENT_NKS_SESSIONS",
    "MIN_VALIDATED_NKS_COVERAGE",
    "MODEL_VERSION",
    "NKS_EVENT_WINDOWS",
    "NRS_RECOVERY_WINDOWS",
    "run_continuous_backtest",
]
