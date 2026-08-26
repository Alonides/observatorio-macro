"""Secondary market-data fallbacks for the provisional Debt/NOK lane.

These sources are used only when a preferred primary-source bridge is not
available. They are explicitly labelled secondary and provisional and remain
subject to the same overlap, age and movement guardrails as every other proxy.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from math import isfinite
from typing import Callable, Mapping
from urllib.parse import urlencode

from ..official import SourceError, _read


YAHOO_BRENT_SYMBOL = "BZ=F"
YAHOO_CHART_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
YAHOO_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
}


def parse_yahoo_chart(payload: Mapping[str, object]) -> list[dict]:
    chart = payload.get("chart")
    if not isinstance(chart, Mapping):
        raise SourceError("Yahoo chart payload has no chart object")
    errors = chart.get("error")
    if errors:
        raise SourceError(f"Yahoo chart error: {errors}")
    result = chart.get("result")
    if not isinstance(result, list) or not result or not isinstance(result[0], Mapping):
        raise SourceError("Yahoo chart payload has no result")
    item = result[0]
    timestamps = item.get("timestamp")
    indicators = item.get("indicators")
    if not isinstance(timestamps, list) or not isinstance(indicators, Mapping):
        raise SourceError("Yahoo chart payload lacks timestamps or indicators")
    quotes = indicators.get("quote")
    if not isinstance(quotes, list) or not quotes or not isinstance(quotes[0], Mapping):
        raise SourceError("Yahoo chart payload lacks quote data")
    closes = quotes[0].get("close")
    if not isinstance(closes, list):
        raise SourceError("Yahoo chart payload lacks close values")

    by_day: dict[str, float] = {}
    for raw_timestamp, raw_close in zip(timestamps, closes):
        if raw_timestamp is None or raw_close is None:
            continue
        try:
            day = datetime.fromtimestamp(float(raw_timestamp), tz=timezone.utc).date().isoformat()
            value = float(raw_close)
        except (TypeError, ValueError, OSError, OverflowError):
            continue
        if isfinite(value) and value > 0.0:
            by_day[day] = value
    if not by_day:
        raise SourceError("Yahoo chart returned no numeric daily closes")
    return [{"date": day, "value": by_day[day]} for day in sorted(by_day)]


def fetch_yahoo_brent(
    read_bytes: Callable[..., bytes] = _read,
    range_value: str = "6mo",
) -> tuple[list[dict], dict]:
    query = urlencode({
        "range": range_value,
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    })
    url = f"{YAHOO_CHART_BASE}/{YAHOO_BRENT_SYMBOL}?{query}"
    try:
        payload = json.loads(
            read_bytes(
                url,
                timeout=10,
                retries=1,
                headers=YAHOO_BROWSER_HEADERS,
            ).decode("utf-8-sig", errors="replace")
        )
    except json.JSONDecodeError as exc:
        raise SourceError(f"Yahoo Brent JSON invalid: {exc}") from exc
    points = parse_yahoo_chart(payload)
    return points, {
        "provider": "Yahoo Finance",
        "url": url,
        "symbol": YAHOO_BRENT_SYMBOL,
        "status": "ok",
        "latest": points[-1]["date"],
        "observations": len(points),
        "role": "secondary delayed Brent futures fallback",
        "secondary": True,
        "provisional_only": True,
    }


__all__ = [
    "YAHOO_BRENT_SYMBOL",
    "fetch_yahoo_brent",
    "parse_yahoo_chart",
]
