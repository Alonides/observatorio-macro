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

NOK_EVENT_WINDOWS = {
    "lehman_2008": ("2008-09-12", "2009-01-31"),
    "oil_2014_15": ("2014-06-01", "2015-03-31"),
    "covid_2020": ("2020-02-19", "2020-04-30"),
    "inflation_2022": ("2022-04-01", "2022-10-31"),
    "banking_2023": ("2023-03-08", "2023-04-05"),
    "tariff_pulse_2025": ("2025-04-02", "2025-04-30"),
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


def _nrs_rows(md: _v4.MarketData) -> list[dict]:
    rows: list[dict] = []
    mapping = {
        "inactive": 0.0,
        "candidate_unconfirmed_residual_missing": 50.0,
        "confirmed": 100.0,
    }
    for day in md.eurnok().dates:
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

    # Re-state NKS event performance using windows designed for NOK rather than
    # only the US sovereign controls in the base backtest.
    nks_rows = _base._block_history(md, "nks")
    output["blocks"]["nks"]["nok_event_windows"] = _event_summary(nks_rows, NOK_EVENT_WINDOWS)

    nrs_rows = _nrs_rows(md)
    nrs_block = _block(nrs_rows, NOK_EVENT_WINDOWS)
    nrs_block["confirmed_sessions"] = sum(row.get("state") == "confirmed" for row in nrs_rows)
    if include_history:
        nrs_block["history"] = nrs_rows
    output["blocks"]["nrs"] = nrs_block

    output["nok_residual"] = residual_diagnostics
    output["method_note_v041"] = (
        "The v0.4.1 continuous test attaches one walk-forward NOK residual "
        "before scoring all sessions. The residual, NKS and NRS therefore use "
        "the same causal history and are not recomputed with future data."
    )
    return output


__all__ = ["MODEL_VERSION", "NOK_EVENT_WINDOWS", "run_continuous_backtest"]
