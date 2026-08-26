"""Secondary market-data fallbacks for the provisional Debt/NOK lane.

These sources are used only when the preferred EIA+CME primary-source bridge is
not available. They are explicitly labelled secondary and provisional and
remain subject to the same overlap, age and movement guardrails as every other
proxy.

Fallback order:

1. AmericasOilWatch public Brent API (underlying Stooq cb.f);
2. Yahoo Finance delayed Brent futures chart.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from math import isfinite
from typing import Callable, Mapping, Sequence
from urllib.parse import urlencode

from ..official import SourceError, _read
from .fast_shapes import parse_dated_price_payload


AMERICAS_BRENT_HISTORY_URL = "https://americasoilwatch.com/api/v1/brent-history"
AMERICAS_BRENT_CURRENT_URL = "https://americasoilwatch.com/api/v1/brent"
AMERICAS_HEADERS = {
    "User-Agent": "observatorio-macro/1.0.3 (+https://github.com/Alonides/observatorio-macro)",
    "Accept": "application/json",
}

YAHOO_BRENT_SYMBOL = "BZ=F"
YAHOO_CHART_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
YAHOO_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
}


def parse_americas_brent(payload: Mapping[str, object] | Sequence[object]) -> list[dict]:
    """Parse only explicit dated USD prices from the public JSON payload."""
    return parse_dated_price_payload(payload)


def _json_request(
    url: str,
    read_bytes: Callable[..., bytes],
    headers: Mapping[str, str],
) -> Mapping[str, object] | Sequence[object]:
    try:
        return json.loads(
            read_bytes(
                url,
                timeout=10,
                retries=2,
                headers=dict(headers),
            ).decode("utf-8-sig", errors="replace")
        )
    except json.JSONDecodeError as exc:
        raise SourceError(f"{url}: JSON inválido: {exc}") from exc


def fetch_americas_brent(
    read_bytes: Callable[..., bytes] = _read,
) -> tuple[list[dict], dict]:
    history_payload = _json_request(
        AMERICAS_BRENT_HISTORY_URL,
        read_bytes,
        AMERICAS_HEADERS,
    )
    points = parse_americas_brent(history_payload)

    current_error = None
    try:
        current_payload = _json_request(
            AMERICAS_BRENT_CURRENT_URL,
            read_bytes,
            AMERICAS_HEADERS,
        )
        current = parse_americas_brent(current_payload)
        by_day = {point["date"]: point for point in points}
        for point in current:
            by_day[point["date"]] = point
        points = [by_day[day] for day in sorted(by_day)]
    except Exception as exc:
        current_error = str(exc)

    return points, {
        "provider": "AmericasOilWatch",
        "underlying": "Stooq cb.f front-month Brent futures",
        "url": AMERICAS_BRENT_HISTORY_URL,
        "current_url": AMERICAS_BRENT_CURRENT_URL,
        "status": "ok",
        "latest": points[-1]["date"],
        "observations": len(points),
        "role": "secondary public Brent futures fallback",
        "secondary": True,
        "provisional_only": True,
        "attribution": "AmericasOilWatch / Stooq",
        "current_endpoint_error": current_error,
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
    payload = _json_request(url, read_bytes, YAHOO_BROWSER_HEADERS)
    if not isinstance(payload, Mapping):
        raise SourceError("Yahoo Brent chart payload is not an object")
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


def fetch_secondary_brent(
    read_bytes: Callable[..., bytes] = _read,
) -> tuple[list[dict], dict, str, dict[str, str]]:
    """Return the first available secondary Brent source plus audit failures."""
    errors: dict[str, str] = {}
    try:
        points, metadata = fetch_americas_brent(read_bytes=read_bytes)
        return points, metadata, "AMERICASOILWATCH_BRENT", errors
    except Exception as exc:
        errors["AMERICASOILWATCH_BRENT"] = str(exc)

    try:
        points, metadata = fetch_yahoo_brent(read_bytes=read_bytes)
        return points, metadata, "YAHOO_BRENT_DELAYED", errors
    except Exception as exc:
        errors["YAHOO_BRENT_DELAYED"] = str(exc)

    raise SourceError("No secondary Brent fallback was available: " + "; ".join(
        f"{key}: {value}" for key, value in sorted(errors.items())
    ))


__all__ = [
    "AMERICAS_BRENT_HISTORY_URL",
    "YAHOO_BRENT_SYMBOL",
    "fetch_americas_brent",
    "fetch_secondary_brent",
    "fetch_yahoo_brent",
    "parse_americas_brent",
    "parse_yahoo_chart",
]
