"""Continuous backtest utilities for the debt/NOK regime model."""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Mapping, Sequence

from .regime import MODEL_VERSION, MarketData, _dss_at, _nks_at, _urp_at


EVENT_WINDOWS = {
    "lehman_2008": ("2008-09-12", "2008-10-10"),
    "us_downgrade_2011": ("2011-07-29", "2011-08-26"),
    "taper_tantrum_2013": ("2013-05-21", "2013-06-24"),
    "risk_off_2018": ("2018-10-03", "2018-12-24"),
    "covid_2020": ("2020-02-19", "2020-03-20"),
    "inflation_2022": ("2022-08-25", "2022-09-23"),
    "banking_2023": ("2023-03-08", "2023-04-05"),
    "tariff_pulse_2025": ("2025-04-02", "2025-04-30"),
}


def _episode_rows(rows: list[dict], threshold: float = 50.0) -> list[dict]:
    episodes: list[dict] = []
    current: list[dict] = []
    for row in rows:
        score = row.get("score")
        active = score is not None and score >= threshold
        if active:
            current.append(row)
        elif current:
            episodes.append(_summarise_episode(current))
            current = []
    if current:
        episodes.append(_summarise_episode(current))
    return episodes


def _summarise_episode(rows: list[dict]) -> dict:
    peak = max(rows, key=lambda item: item["score"])
    return {
        "start": rows[0]["date"],
        "end": rows[-1]["date"],
        "sessions": len(rows),
        "peak_score": round(peak["score"], 2),
        "peak_date": peak["date"],
        "peak_state": peak.get("state"),
    }


def _block_history(md: MarketData, block: str) -> list[dict]:
    reference = md.view("DGS30")
    if block == "nks" and md.eurnok().dates:
        reference = md.eurnok()
    evaluator = {"urp": _urp_at, "dss": _dss_at, "nks": _nks_at}[block]
    output = []
    for day in reference.dates:
        result = evaluator(md, day)
        output.append({
            "date": day.isoformat(),
            "score": result.get("score"),
            "state": result.get("state"),
        })
    return output


def _event_summary(rows: list[dict], windows: Mapping[str, tuple[str, str]] = EVENT_WINDOWS) -> dict:
    result = {}
    for name, (start_raw, end_raw) in windows.items():
        start = date.fromisoformat(start_raw)
        end = date.fromisoformat(end_raw)
        selected = [row for row in rows if start <= date.fromisoformat(row["date"]) <= end and row["score"] is not None]
        if not selected:
            result[name] = {"available": False, "start": start_raw, "end": end_raw}
            continue
        peak = max(selected, key=lambda item: item["score"])
        result[name] = {
            "available": True,
            "start": start_raw,
            "end": end_raw,
            "observations": len(selected),
            "peak_score": round(peak["score"], 2),
            "peak_date": peak["date"],
            "peak_state": peak.get("state"),
            "days_ge_50": sum(row["score"] >= 50.0 for row in selected),
        }
    return result


def _annual_alert_counts(rows: list[dict], threshold: float = 50.0) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        if row["score"] is not None and row["score"] >= threshold:
            counter[row["date"][:4]] += 1
    return dict(sorted(counter.items()))


def run_continuous_backtest(
    series: Mapping[str, Sequence[Mapping[str, object]]],
    include_history: bool = False,
) -> dict:
    """Run the frozen v0.3 classifier over every available reference session."""
    md = MarketData(series)
    histories = {block: _block_history(md, block) for block in ("urp", "dss", "nks")}
    output = {
        "model_version": MODEL_VERSION,
        "coverage": {
            series_id: {
                "observations": len(md.view(series_id).dates),
                "start": md.view(series_id).dates[0].isoformat() if md.view(series_id).dates else None,
                "end": md.view(series_id).dates[-1].isoformat() if md.view(series_id).dates else None,
            }
            for series_id in (
                "DGS10", "DGS30", "DFII10", "DTWEXBGS", "DEXUSEU", "DEXNOUS",
                "DEXSDUS", "VIXCLS", "GOLDAMGBD228NLBM", "DCOILBRENTEU",
                "IRLTLT01DEM156N", "IRLTLT01NOM156N",
            )
        },
        "blocks": {},
    }
    for block, rows in histories.items():
        scored = [row for row in rows if row["score"] is not None]
        output["blocks"][block] = {
            "scored_sessions": len(scored),
            "episodes_ge_50": _episode_rows(rows),
            "annual_alert_sessions_ge_50": _annual_alert_counts(rows),
            "event_windows": _event_summary(rows),
            "max_score": round(max((row["score"] for row in scored), default=0.0), 2),
        }
        if include_history:
            output["blocks"][block]["history"] = rows
    return output


__all__ = ["EVENT_WINDOWS", "run_continuous_backtest"]
