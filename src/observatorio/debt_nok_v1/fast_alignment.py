"""Lag-aware overlap validation and v1.0.3 runtime configuration.

Primary sources often label the same economic move on adjacent business days
because their fixing or publication cut-offs differ. Validation therefore tests
a frozen set of lags (-2 to +2 business days) and reports the best alignment.
This affects only proxy admissibility, never the model observation dates.

Importing this module installs three deliberate provisional-only hooks before
the scheduled agent imports their public functions:

* the lag-aware validator;
* the frozen direct-FX calibration;
* an AmericasOilWatch-first Brent fallback, retaining Yahoo only as last resort.

The authoritative model and official histories are not touched.
"""

from __future__ import annotations

from datetime import date, timedelta
from math import isfinite, log, sqrt
from statistics import mean
from typing import Mapping, Sequence

from . import fast_bridge as _bridge
from . import fast_fallbacks as _fallbacks
from .fast_config import configure_v103_rules


def _point_map(points: Sequence[Mapping[str, object]]) -> dict[date, float]:
    output: dict[date, float] = {}
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
        if isfinite(value) and value > 0.0:
            output[day] = value
    return output


def _returns(points: Sequence[Mapping[str, object]]) -> dict[date, float]:
    values = _point_map(points)
    ordered = sorted(values)
    output: dict[date, float] = {}
    for previous, current in zip(ordered, ordered[1:]):
        if (current - previous).days > 7:
            continue
        try:
            output[current] = log(values[current] / values[previous])
        except (ValueError, ZeroDivisionError):
            continue
    return output


def _shift_business_days(day: date, sessions: int) -> date:
    if sessions == 0:
        return day
    direction = 1 if sessions > 0 else -1
    remaining = abs(sessions)
    current = day
    while remaining:
        current += timedelta(days=direction)
        if current.weekday() < 5:
            remaining -= 1
    return current


def _correlation(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_mean = mean(left)
    right_mean = mean(right)
    left_var = sum((value - left_mean) ** 2 for value in left)
    right_var = sum((value - right_mean) ** 2 for value in right)
    if left_var <= 1e-18 or right_var <= 1e-18:
        return None
    covariance = sum(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left, right)
    )
    return covariance / sqrt(left_var * right_var)


def _candidate(
    official_returns: Mapping[date, float],
    proxy_returns: Mapping[date, float],
    lag: int,
    window: int,
) -> dict:
    pairs: list[tuple[date, float, float]] = []
    for official_day in sorted(official_returns):
        proxy_day = _shift_business_days(official_day, lag)
        proxy_value = proxy_returns.get(proxy_day)
        if proxy_value is None:
            continue
        pairs.append((official_day, official_returns[official_day], proxy_value))
    pairs = pairs[-window:]
    left = [item[1] for item in pairs]
    right = [item[2] for item in pairs]
    correlation = _correlation(left, right)
    mae = mean(abs(a - b) for a, b in zip(left, right)) * 100.0 if left else None
    sign = mean(1.0 if a * b >= 0.0 else 0.0 for a, b in zip(left, right)) if left else None
    return {
        "proxy_lag_business_days": lag,
        "overlap_returns": len(pairs),
        "correlation": correlation,
        "mae_pct_points": mae,
        "sign_agreement": sign,
        "overlap_start": pairs[0][0].isoformat() if pairs else None,
        "overlap_end": pairs[-1][0].isoformat() if pairs else None,
    }


def tracking_statistics_aligned(
    official_points: Sequence[Mapping[str, object]],
    proxy_points: Sequence[Mapping[str, object]],
    window: int = 60,
) -> dict:
    official_returns = _returns(official_points)
    proxy_returns = _returns(proxy_points)
    candidates = [
        _candidate(official_returns, proxy_returns, lag, window)
        for lag in (-2, -1, 0, 1, 2)
    ]
    eligible = [item for item in candidates if item["correlation"] is not None]
    if not eligible:
        best = max(candidates, key=lambda item: item["overlap_returns"], default={})
    else:
        best = max(
            eligible,
            key=lambda item: (
                item["correlation"],
                -float(item["mae_pct_points"] or 1e9),
                item["overlap_returns"],
                -abs(item["proxy_lag_business_days"]),
            ),
        )
    output = dict(best)
    for key in ("correlation", "mae_pct_points", "sign_agreement"):
        value = output.get(key)
        output[key] = None if value is None else round(float(value), 4)
    output["alignment_method"] = "best fixed business-day lag in {-2,-1,0,1,2}"
    output["candidate_summary"] = [
        {
            "lag": item["proxy_lag_business_days"],
            "n": item["overlap_returns"],
            "corr": None if item["correlation"] is None else round(float(item["correlation"]), 4),
            "mae": None if item["mae_pct_points"] is None else round(float(item["mae_pct_points"]), 4),
        }
        for item in candidates
    ]
    return output


_original_yahoo_fetch = _fallbacks.fetch_yahoo_brent


def _secondary_brent_for_agent(*args, **kwargs):
    """Preserve the agent's import contract while preferring the public API."""
    try:
        points, metadata = _fallbacks.fetch_americas_brent(*args, **kwargs)
        metadata = dict(metadata)
        metadata["source_id"] = "AMERICASOILWATCH_BRENT"
        return points, metadata
    except Exception as americas_error:
        try:
            points, metadata = _original_yahoo_fetch(*args, **kwargs)
        except Exception as yahoo_error:
            raise RuntimeError(
                "AmericasOilWatch failed: " + str(americas_error)
                + "; Yahoo Finance failed: " + str(yahoo_error)
            ) from yahoo_error
        metadata = dict(metadata)
        metadata["source_id"] = "YAHOO_BRENT_DELAYED"
        metadata["preferred_source_error"] = str(americas_error)
        return points, metadata


_original_lane_payload = _bridge.build_fast_lane_payload


def _lane_payload_with_source_labels(official_result: dict, provisional_result: dict, bridge: dict) -> dict:
    payload = _original_lane_payload(official_result, provisional_result, bridge)
    sources = bridge.get("sources") if isinstance(bridge.get("sources"), dict) else {}
    fallback = sources.get("YAHOO_BRENT_DELAYED") if isinstance(sources.get("YAHOO_BRENT_DELAYED"), dict) else {}
    target = bridge.get("targets", {}).get("DCOILBRENTEU") if isinstance(bridge.get("targets"), dict) else None
    if isinstance(target, dict) and fallback.get("status") == "ok":
        source_id = fallback.get("source_id")
        if source_id == "AMERICASOILWATCH_BRENT":
            target["label"] = "AmericasOilWatch / Stooq delayed Brent futures fallback"
            target["proxy"] = source_id
            target["secondary_source"] = True
        elif source_id == "YAHOO_BRENT_DELAYED":
            target["label"] = "Yahoo Finance delayed Brent futures fallback"
            target["proxy"] = source_id
            target["secondary_source"] = True
    return payload


# Install provisional runtime hooks once per process. The scheduled agent imports
# these public names only after importing this module.
_bridge.tracking_statistics = tracking_statistics_aligned
_bridge.RULES = configure_v103_rules(_bridge.RULES)
_bridge.build_fast_lane_payload = _lane_payload_with_source_labels
_fallbacks.fetch_yahoo_brent = _secondary_brent_for_agent


__all__ = ["tracking_statistics_aligned"]
