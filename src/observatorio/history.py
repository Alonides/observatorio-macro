"""Historical data ingestion for the continuous 2006-present backtest.

Operational daily collection in the repository remains unchanged. This module
is a separate, explicit backtest loader that requests long histories from the
original public producers and records coverage and failures per series.
"""

from __future__ import annotations

import csv
import io
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


USER_AGENT = "observatorio-macro-backtest/0.3 (+https://github.com/Alonides/observatorio-macro)"

BACKTEST_SERIES = (
    "DGS10",
    "DGS30",
    "DFII10",
    "DTWEXBGS",
    "DEXUSEU",
    "DEXNOUS",
    "DEXSDUS",
    "VIXCLS",
    "GOLDAMGBD228NLBM",
    "DCOILBRENTEU",
    "IRLTLT01DEM156N",
    "IRLTLT01NOM156N",
)

FED_PACKAGES = {
    "indexes": "122e3bcb627e8e53f1bf72a1a09cfb81",
    "rates": "60f32914ab61dfab590e0e470153e3ae",
}

FED_MAP = {
    "DTWEXBGS": ("indexes", "JRXWTFB_N.B"),
    "DEXUSEU": ("rates", "RXI$US_N.B.EU"),
    "DEXNOUS": ("rates", "RXI_N.B.NO"),
    "DEXSDUS": ("rates", "RXI_N.B.SD"),
}

TREASURY_MAP = {
    "DGS10": ("daily_treasury_yield_curve", "10 Yr"),
    "DGS30": ("daily_treasury_yield_curve", "30 Yr"),
    "DFII10": ("daily_treasury_real_yield_curve", "10 YR"),
}


class HistorySourceError(RuntimeError):
    pass


def _read(url: str, timeout: int = 45, retries: int = 3, headers: dict[str, str] | None = None) -> bytes:
    merged_headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        merged_headers.update(headers)
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = Request(url, headers=merged_headers)
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    raise HistorySourceError(f"{url}: {last_error}")


def _text(url: str, encoding: str = "utf-8-sig") -> str:
    return _read(url).decode(encoding, errors="replace")


def _numeric(raw) -> float | None:
    if raw is None:
        return None
    value = str(raw).strip().replace("\u00a0", "").replace(" ", "")
    if value in {"", ".", "..", "...", "ND", "NA", "N/A", "null", "None", "-"}:
        return None
    if value.startswith("(") and value.endswith(")"):
        value = f"-{value[1:-1]}"
    value = value.replace(",", "").lstrip("+")
    try:
        return float(value)
    except ValueError:
        return None


def _iso_day(raw: str) -> str | None:
    raw = str(raw).strip()
    for fmt in (
        "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y",
        "%d %b %Y", "%d-%b-%Y", "%b %d, %Y", "%B %d, %Y",
    ):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def _dedupe(points: list[dict], start: str | None = None, end: str | None = None) -> list[dict]:
    by_day = {}
    for point in points:
        day = point.get("date")
        value = point.get("value")
        if day is None or value is None:
            continue
        day = str(day)
        if start and day < start:
            continue
        if end and day > end:
            continue
        by_day[day] = {"date": day, "value": float(value)}
    return [by_day[day] for day in sorted(by_day)]


def _parse_treasury_csv(text: str, column: str) -> list[dict]:
    points = []
    for row in csv.DictReader(io.StringIO(text)):
        day = _iso_day(row.get("Date") or "")
        value = _numeric(row.get(column))
        if day and value is not None:
            points.append({"date": day, "value": value})
    return _dedupe(points)


def _parse_fed_ddp(text: str, code: str) -> list[dict]:
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if line.lstrip('"').startswith("Time Period")), None)
    if start is None:
        raise HistorySourceError("Federal Reserve DDP header not found")
    points = []
    for row in csv.DictReader(io.StringIO("\n".join(lines[start:]))):
        day = _iso_day(row.get("Time Period") or "")
        value = _numeric(row.get(code))
        if day and value is not None:
            points.append({"date": day, "value": value})
    return _dedupe(points)


def _parse_sdmx_csv(text: str) -> list[dict]:
    lines = [line for line in text.splitlines() if line.strip()]
    start = next(
        (index for index, line in enumerate(lines) if "TIME_PERIOD" in line.upper() and "OBS_VALUE" in line.upper()),
        None,
    )
    if start is None:
        raise HistorySourceError("SDMX header not found")
    sample = "\n".join(lines[start:start + 4])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    points = []
    for row in csv.DictReader(io.StringIO("\n".join(lines[start:])), dialect=dialect):
        upper = {str(key).strip().upper(): value for key, value in row.items() if key}
        day = _iso_day(upper.get("TIME_PERIOD") or "")
        value = _numeric(upper.get("OBS_VALUE"))
        if day and value is not None:
            points.append({"date": day, "value": value})
    return _dedupe(points)


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None


def _treasury_history(series_id: str, start: str, end: str) -> list[dict]:
    kind, column = TREASURY_MAP[series_id]
    start_year = date.fromisoformat(start).year
    end_year = date.fromisoformat(end).year
    points: list[dict] = []
    for year in range(start_year, end_year + 1):
        url = (
            "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
            f"daily-treasury-rates.csv/{year}/all?type={kind}&field_tdr_date_value={year}"
            "&page&_format=csv"
        )
        points.extend(_parse_treasury_csv(_text(url), column))
    return _dedupe(points, start, end)


def _fed_history(series_id: str, start: str, end: str) -> list[dict]:
    package, code = FED_MAP[series_id]
    package_id = FED_PACKAGES[package]
    url = (
        "https://www.federalreserve.gov/datadownload/Output.aspx?"
        f"rel=H10&series={package_id}&lastobs=20000"
        "&filetype=csv&label=include&layout=seriescolumn"
    )
    return _dedupe(_parse_fed_ddp(_text(url), code), start, end)


def _vix_history(start: str, end: str) -> list[dict]:
    points = []
    for row in csv.DictReader(io.StringIO(_text("https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"))):
        day = _iso_day(row.get("DATE") or "")
        value = _numeric(row.get("CLOSE"))
        if day and value is not None:
            points.append({"date": day, "value": value})
    return _dedupe(points, start, end)


def _gold_history(start: str, end: str) -> list[dict]:
    payload = json.loads(_read(
        "https://prices.lbma.org.uk/json/gold_am.json",
        headers={"Accept": "application/json", "Referer": "https://www.lbma.org.uk/"},
    ).decode("utf-8-sig", errors="replace"))
    points = []
    for row in payload:
        values = row.get("v") or []
        value = _numeric(values[0] if values else None)
        day = _iso_day(row.get("d") or "")
        if day and value is not None:
            points.append({"date": day, "value": value})
    return _dedupe(points, start, end)


def _brent_history(start: str, end: str) -> list[dict]:
    query = (
        "api_key=DEMO_KEY&frequency=daily&data[0]=value"
        "&facets[series][]=RBRTE"
        f"&start={start}&end={end}"
        "&sort[0][column]=period&sort[0][direction]=asc&offset=0&length=10000"
    )
    payload = json.loads(_read(
        "https://api.eia.gov/v2/petroleum/pri/spt/data/?" + query
    ).decode("utf-8-sig", errors="replace"))
    if payload.get("error"):
        raise HistorySourceError(f"EIA: {payload['error']}")
    points = []
    for row in payload.get("response", {}).get("data", []):
        day = _iso_day(row.get("period") or "")
        value = _numeric(row.get("value"))
        if day and value is not None:
            points.append({"date": day, "value": value})
    return _dedupe(points, start, end)


def _bund_history(start: str, end: str) -> list[dict]:
    query = urlencode({"format": "sdmx_csv", "lang": "en", "startPeriod": start, "endPeriod": end})
    url = (
        "https://api.statistiken.bundesbank.de/rest/data/BBSSY/"
        "D.REN.EUR.A630.000000WT1010.A?" + query
    )
    return _dedupe(_parse_sdmx_csv(_text(url)), start, end)


def _norway_history(start: str, end: str) -> list[dict]:
    text = _text(
        "https://www.norges-bank.no/en/topics/Statistics/"
        "norwegian-government-securities/generiske-statsrenter/"
    )
    parser = _TableParser()
    parser.feed(text)
    points = []
    for row in parser.rows:
        if len(row) < 8:
            continue
        day = _iso_day(row[0])
        value = _numeric(row[7])
        if day and value is not None:
            points.append({"date": day, "value": value})
    if not points:
        raise HistorySourceError("Norges Bank generic yield table not recognised")
    return _dedupe(points, start, end)


def fetch_historical_series(series_id: str, start: str = "2006-01-01", end: str | None = None) -> list[dict]:
    end = end or date.today().isoformat()
    if series_id in TREASURY_MAP:
        return _treasury_history(series_id, start, end)
    if series_id in FED_MAP:
        return _fed_history(series_id, start, end)
    if series_id == "VIXCLS":
        return _vix_history(start, end)
    if series_id == "GOLDAMGBD228NLBM":
        return _gold_history(start, end)
    if series_id == "DCOILBRENTEU":
        return _brent_history(start, end)
    if series_id == "IRLTLT01DEM156N":
        return _bund_history(start, end)
    if series_id == "IRLTLT01NOM156N":
        return _norway_history(start, end)
    raise HistorySourceError(f"No historical adapter for {series_id}")


def fetch_history_dataset(
    start: str = "2006-01-01",
    end: str | None = None,
    workers: int = 6,
) -> dict:
    end = end or date.today().isoformat()
    series: dict[str, list[dict]] = {}
    errors: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="backtest-source") as pool:
        futures = {pool.submit(fetch_historical_series, series_id, start, end): series_id for series_id in BACKTEST_SERIES}
        for future in as_completed(futures):
            series_id = futures[future]
            try:
                points = future.result()
                series[series_id] = points
                print(f"OK {series_id}: {len(points)} observations", flush=True)
            except Exception as exc:
                errors.append({"series_id": series_id, "error": str(exc)})
                print(f"ERROR {series_id}: {exc}", flush=True)
    coverage = {
        series_id: {
            "observations": len(points),
            "start": points[0]["date"] if points else None,
            "end": points[-1]["date"] if points else None,
        }
        for series_id, points in sorted(series.items())
    }
    return {
        "schema_version": 1,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "requested_start": start,
        "requested_end": end,
        "series": series,
        "coverage": coverage,
        "errors": sorted(errors, key=lambda item: item["series_id"]),
        "method_note": (
            "Long-history backtest loader. Norges Bank generic 10-year coverage may start later "
            "than 2006; missing pre-generic history is reported and never fabricated."
        ),
    }


def write_history_dataset(path: str | Path, payload: dict) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)


__all__ = [
    "BACKTEST_SERIES",
    "HistorySourceError",
    "fetch_historical_series",
    "fetch_history_dataset",
    "write_history_dataset",
]
