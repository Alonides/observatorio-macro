"""Adaptadores sin clave para fuentes oficiales y públicas.

FRED sigue siendo una referencia útil, pero su servidor CSV no respondió desde
GitHub Actions. Este módulo evita ese punto único de fallo y consulta a los
productores primarios siempre que existe una descarga automatizable.
"""

from __future__ import annotations

import csv
import io
import json
import time
from concurrent.futures import Future
from datetime import date, datetime, timezone
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class SourceError(RuntimeError):
    pass


_CACHE: dict[str, Future] = {}
_CACHE_LOCK = Lock()


def _memo(key: str, loader):
    """Comparte una sola descarga entre series concurrentes del mismo paquete."""
    owner = False
    with _CACHE_LOCK:
        future = _CACHE.get(key)
        if future is None:
            future = Future()
            _CACHE[key] = future
            owner = True
    if owner:
        try:
            future.set_result(loader())
        except BaseException as exc:
            future.set_exception(exc)
    return future.result()


def _read(url: str, timeout: int = 25, retries: int = 2) -> bytes:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = Request(url, headers={"User-Agent": "observatorio-macro/0.2 (public-data collector)"})
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(1.5)
    raise SourceError(f"{url}: {last_error}")


def _text(url: str) -> str:
    return _read(url).decode("utf-8-sig", errors="replace")


def _json(url: str):
    try:
        return json.loads(_text(url))
    except json.JSONDecodeError as exc:
        raise SourceError(f"JSON no válido en {url}: {exc}") from exc


def _numeric(raw) -> float | None:
    if raw is None:
        return None
    value = str(raw).strip().replace(",", "")
    if value in {"", ".", "ND", "NA", "N/A", "null", "None"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_treasury_csv(text: str) -> dict[str, list[dict]]:
    output: dict[str, list[dict]] = {}
    for row in csv.DictReader(io.StringIO(text)):
        raw_date = (row.get("Date") or "").strip()
        if not raw_date:
            continue
        try:
            day = datetime.strptime(raw_date, "%m/%d/%Y").date().isoformat()
        except ValueError:
            continue
        for column, raw in row.items():
            if column == "Date":
                continue
            value = _numeric(raw)
            if value is not None:
                output.setdefault(column.strip(), []).append({"date": day, "value": value})
    for points in output.values():
        points.sort(key=lambda item: item["date"])
    return output


def parse_fed_ddp_csv(text: str) -> dict[str, list[dict]]:
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.lstrip('"').startswith("Time Period")), None)
    if start is None:
        raise SourceError("Federal Reserve DDP: no se encontró Time Period")
    output: dict[str, list[dict]] = {}
    for row in csv.DictReader(io.StringIO("\n".join(lines[start:]))):
        day = (row.get("Time Period") or "").strip()
        try:
            date.fromisoformat(day)
        except ValueError:
            continue
        for column, raw in row.items():
            if column == "Time Period":
                continue
            value = _numeric(raw)
            if value is not None:
                output.setdefault(column.strip(), []).append({"date": day, "value": value})
    return output


def parse_sofr_json(payload: dict) -> list[dict]:
    points = []
    for row in payload.get("refRates", []):
        value = _numeric(row.get("percentRate"))
        day = row.get("effectiveDate")
        if value is not None and day:
            points.append({"date": day, "value": value})
    return sorted(points, key=lambda item: item["date"])


def _treasury(kind: str) -> dict[str, list[dict]]:
    def load():
        merged: dict[str, list[dict]] = {}
        current_year = date.today().year
        for year in (current_year - 1, current_year):
            url = (
                f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
                f"daily-treasury-rates.csv/{year}/all?type={kind}&field_tdr_date_value={year}"
                f"&page&_format=csv"
            )
            for column, points in parse_treasury_csv(_text(url)).items():
                merged.setdefault(column, []).extend(points)
        for points in merged.values():
            unique = {item["date"]: item for item in points}
            points[:] = sorted(unique.values(), key=lambda item: item["date"])
        return merged
    return _memo(f"treasury:{kind}", load)


FED_PACKAGES = {
    "indexes": "122e3bcb627e8e53f1bf72a1a09cfb81",
    "rates": "60f32914ab61dfab590e0e470153e3ae",
}


def _fed_h10(package: str) -> dict[str, list[dict]]:
    def load():
        series = FED_PACKAGES[package]
        url = (
            "https://www.federalreserve.gov/datadownload/Output.aspx?"
            f"rel=H10&series={series}&lastobs=100&filetype=csv&label=include&layout=seriescolumn"
        )
        return parse_fed_ddp_csv(_text(url))
    return _memo(f"fed-h10:{package}", load)


def _sofr() -> list[dict]:
    return _memo(
        "nyfed:sofr",
        lambda: parse_sofr_json(_json("https://markets.newyorkfed.org/api/rates/secured/sofr/last/100.json")),
    )


def _fiscal_debt() -> list[dict]:
    def load():
        url = (
            "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/"
            "accounting/od/debt_to_penny?sort=-record_date&page%5Bsize%5D=500"
        )
        points = []
        for row in _json(url).get("data", []):
            value = _numeric(row.get("tot_pub_debt_out_amt"))
            if value is not None:
                points.append({"date": row["record_date"], "value": value / 1_000_000})
        return sorted(points, key=lambda item: item["date"])
    return _memo("fiscal:debt", load)


def _gold() -> list[dict]:
    def load():
        points = []
        for row in _json("https://prices.lbma.org.uk/json/gold_am.json"):
            values = row.get("v") or []
            value = _numeric(values[0] if values else None)
            if value is not None:
                points.append({"date": row["d"], "value": value})
        return points[-900:]
    return _memo("lbma:gold-am", load)


def _bitcoin() -> list[dict]:
    def load():
        payload = _json("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=365&interval=daily")
        by_day = {}
        for timestamp_ms, raw in payload.get("prices", []):
            day = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).date().isoformat()
            value = _numeric(raw)
            if value is not None:
                by_day[day] = {"date": day, "value": value}
        return sorted(by_day.values(), key=lambda item: item["date"])
    return _memo("coingecko:btc", load)


def _vix() -> list[dict]:
    def load():
        points = []
        text = _text("https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv")
        for row in csv.DictReader(io.StringIO(text)):
            try:
                day = datetime.strptime(row["DATE"], "%m/%d/%Y").date().isoformat()
            except (KeyError, ValueError):
                continue
            value = _numeric(row.get("CLOSE"))
            if value is not None:
                points.append({"date": day, "value": value})
        return points[-900:]
    return _memo("cboe:vix", load)


NOMINAL_MAP = {"DGS3MO": "3 Mo", "DGS2": "2 Yr", "DGS10": "10 Yr", "DGS30": "30 Yr"}
H10_RATES_MAP = {
    "DEXUSEU": "RXI$US_N.B.EU",
    "DEXNOUS": "RXI_N.B.NO",
    "DEXJPUS": "RXI_N.B.JA",
    "DEXCHUS": "RXI_N.B.CH",
}


def fetch_series(series_id: str) -> list[dict]:
    if series_id in NOMINAL_MAP:
        points = _treasury("daily_treasury_yield_curve").get(NOMINAL_MAP[series_id], [])
    elif series_id == "DFII10":
        points = _treasury("daily_treasury_real_yield_curve").get("10 YR", [])
    elif series_id == "T10YIE":
        nominal = {p["date"]: p["value"] for p in fetch_series("DGS10")}
        real = {p["date"]: p["value"] for p in fetch_series("DFII10")}
        points = [{"date": day, "value": nominal[day] - real[day]} for day in sorted(nominal.keys() & real.keys())]
    elif series_id == "DTWEXBGS":
        points = _fed_h10("indexes").get("JRXWTFB_N.B", [])
    elif series_id in H10_RATES_MAP:
        points = _fed_h10("rates").get(H10_RATES_MAP[series_id], [])
    elif series_id == "SOFR":
        points = _sofr()
    elif series_id == "GFDEBTN":
        points = _fiscal_debt()
    elif series_id == "GOLDAMGBD228NLBM":
        points = _gold()
    elif series_id == "CBBTCUSD":
        points = _bitcoin()
    elif series_id == "VIXCLS":
        points = _vix()
    else:
        raise SourceError(f"{series_id}: fuente oficial aún no incorporada en v0.2")

    if not points:
        raise SourceError(f"{series_id}: la fuente respondió sin observaciones")
    return points


CORE_SERIES = frozenset({
    "DGS2", "DGS10", "DGS30", "DFII10", "T10YIE",
    "DTWEXBGS", "DEXUSEU", "DEXNOUS", "DEXJPUS", "DEXCHUS", "SOFR",
})

