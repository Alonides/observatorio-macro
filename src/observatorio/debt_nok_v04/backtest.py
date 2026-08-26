"""Continuous v0.4 backtest, including the persistent URR state."""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Mapping, Sequence

# Importing the overlay first patches the falsified v0.3 risk gate.
from . import regime as _v4
from .. import backtest as _base

MODEL_VERSION = _v4.MODEL_VERSION


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


def _event_summary(rows: list[dict]) -> dict:
    windows = getattr(_base, "EVENT_WINDOWS", {})
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
        }
    return result


def run_continuous_backtest(
    series: Mapping[str, Sequence[Mapping[str, object]]],
    include_history: bool = False,
) -> dict:
    output = _base.run_continuous_backtest(series, include_history=include_history)
    output["model_version"] = MODEL_VERSION

    md = _v4.MarketData(series)
    rows = _urr_rows(md)
    scored = [row for row in rows if row["score"] is not None]
    block = {
        "scored_sessions": len(scored),
        "episodes_ge_50": _episodes(rows),
        "annual_alert_sessions_ge_50": _annual(rows),
        "event_windows": _event_summary(rows),
        "max_score": round(max((row["score"] for row in scored), default=0.0), 2),
    }
    if include_history:
        block["history"] = rows
    output.setdefault("blocks", {})["urr"] = block
    output["method_note_v04"] = (
        "The v0.4 continuous test uses a fresh risk-off onset and reports URR "
        "separately from the short-lived URP pulse."
    )
    return output


__all__ = ["MODEL_VERSION", "run_continuous_backtest"]
