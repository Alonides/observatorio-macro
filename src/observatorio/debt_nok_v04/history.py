"""Historical loaders used by the v0.4.1 continuous backtest.

The operational daily collector is not changed. This overlay fixes the long
history needed by the research model:

* Federal Reserve H.10 requests use 6,000 observations;
* EIA Brent is paginated beyond the 5,000-row response limit;
* Norway 10-year yields come from Norges Bank's official SDMX data warehouse
  instead of the short HTML table shown on the public page.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlencode

from .. import history as _base

BACKTEST_SERIES = _base.BACKTEST_SERIES
HistorySourceError = _base.HistorySourceError


@lru_cache(maxsize=8)
def _fed_package_text(package_id: str) -> str:
    url = (
        "https://www.federalreserve.gov/datadownload/Output.aspx?"
        f"rel=H10&series={package_id}&lastobs=6000"
        "&filetype=csv&label=include&layout=seriescolumn"
    )
    return _base._text(url)


def _fed_history(series_id: str, start: str, end: str) -> list[dict]:
    package, code = _base.FED_MAP[series_id]
    package_id = _base.FED_PACKAGES[package]
    text = _fed_package_text(package_id)
    return _base._dedupe(_base._parse_fed_ddp(text, code), start, end)


def _brent_history(start: str, end: str) -> list[dict]:
    points: list[dict] = []
    offset = 0
    page_size = 5000
    while True:
        query = (
            "api_key=DEMO_KEY&frequency=daily&data[0]=value"
            "&facets[series][]=RBRTE"
            f"&start={start}&end={end}"
            "&sort[0][column]=period&sort[0][direction]=asc"
            f"&offset={offset}&length={page_size}"
        )
        payload = json.loads(
            _base._read(
                "https://api.eia.gov/v2/petroleum/pri/spt/data/?" + query
            ).decode("utf-8-sig", errors="replace")
        )
        if payload.get("error"):
            raise HistorySourceError(f"EIA: {payload['error']}")
        response = payload.get("response", {})
        rows = response.get("data", [])
        for row in rows:
            day = _base._iso_day(row.get("period") or "")
            value = _base._numeric(row.get("value"))
            if day and value is not None:
                points.append({"date": day, "value": value})
        offset += len(rows)
        try:
            total = int(response.get("total") or 0)
        except (TypeError, ValueError):
            total = 0
        if not rows or (total and offset >= total) or len(rows) < page_size:
            break
    return _base._dedupe(points, start, end)


def _norway_history(start: str, end: str) -> list[dict]:
    query = urlencode({
        "format": "csv",
        "locale": "en",
        "startPeriod": start,
        "endPeriod": end,
    })
    url = (
        "https://data.norges-bank.no/api/data/GOVT_GENERIC_RATES/"
        "B.10Y.GBON.?" + query
    )
    points = _base._parse_sdmx_csv(_base._text(url))
    points = _base._dedupe(points, start, end)
    if not points:
        raise HistorySourceError("Norges Bank SDMX returned no 10-year government yield observations")
    return points


# The base dispatcher looks up these globals when each series is requested.
_base._fed_history = _fed_history
_base._brent_history = _brent_history
_base._norway_history = _norway_history

fetch_historical_series = _base.fetch_historical_series
fetch_history_dataset = _base.fetch_history_dataset
write_history_dataset = _base.write_history_dataset


def write_dataset(path: str | Path, payload: dict) -> None:
    write_history_dataset(path, payload)


__all__ = [
    "BACKTEST_SERIES",
    "HistorySourceError",
    "fetch_historical_series",
    "fetch_history_dataset",
    "write_history_dataset",
    "write_dataset",
]
