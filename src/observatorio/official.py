"""Adaptadores sin secretos para fuentes primarias y públicas.

El recolector evita un único proveedor: cada bloque consulta al productor del
dato. Los parsers son independientes de la red y están cubiertos por pruebas.
"""

from __future__ import annotations

import csv
import io
import json
import re
import time
from concurrent.futures import Future
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class SourceError(RuntimeError):
    pass


_CACHE: dict[str, Future] = {}
_CACHE_LOCK = Lock()
USER_AGENT = "observatorio-macro/0.3 (+https://github.com/Alonides/observatorio-macro)"


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


def _read(
    url: str,
    timeout: int = 30,
    retries: int = 2,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> bytes:
    last_error: Exception | None = None
    merged_headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        merged_headers.update(headers)
    for attempt in range(retries):
        try:
            request = Request(url, data=data, headers=merged_headers)
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(1.25 * (attempt + 1))
    raise SourceError(f"{url}: {last_error}")


def _text(url: str, encoding: str = "utf-8-sig") -> str:
    return _read(url).decode(encoding, errors="replace")


def _json(url: str, data: bytes | None = None, headers: dict[str, str] | None = None):
    try:
        return json.loads(_read(url, data=data, headers=headers).decode("utf-8-sig", errors="replace"))
    except json.JSONDecodeError as exc:
        raise SourceError(f"JSON no válido en {url}: {exc}") from exc


def _numeric(raw) -> float | None:
    if raw is None:
        return None
    value = str(raw).strip().replace("\u00a0", "").replace(" ", "")
    if value in {"", ".", "..", "...", "ND", "NA", "N/A", "(NA)", "null", "None", "-"}:
        return None
    if value.startswith("(") and value.endswith(")"):
        value = f"-{value[1:-1]}"
    # Las descargas se solicitan en inglés y usan punto decimal. La coma es
    # siempre separador de miles (H.4.1 y BEA incluyen cifras como 936,406).
    value = value.replace(",", "")
    value = value.lstrip("+")
    try:
        return float(value)
    except ValueError:
        return None


def _iso_day(raw: str) -> str | None:
    raw = str(raw).strip()
    if not raw:
        return None
    formats = (
        "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y",
        "%d %b %Y", "%d-%b-%Y", "%b %d, %Y", "%B %d, %Y",
    )
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    reiwa = re.fullmatch(r"R\s*(\d{1,2})[./-](\d{1,2})[./-](\d{1,2})", raw, flags=re.I)
    if reiwa:
        year, month, day = map(int, reiwa.groups())
        return date(2018 + year, month, day).isoformat()
    quarter = re.fullmatch(r"(\d{4})-?Q([1-4])", raw, flags=re.I)
    if quarter:
        year, q = map(int, quarter.groups())
        next_start = date(year + (q == 4), 1 if q == 4 else q * 3 + 1, 1)
        return (next_start - timedelta(days=1)).isoformat()
    return None


def _dedupe(points: list[dict]) -> list[dict]:
    return sorted({item["date"]: item for item in points}.values(), key=lambda item: item["date"])


def parse_treasury_csv(text: str) -> dict[str, list[dict]]:
    output: dict[str, list[dict]] = {}
    for row in csv.DictReader(io.StringIO(text)):
        day = _iso_day(row.get("Date") or "")
        if not day:
            continue
        for column, raw in row.items():
            if column == "Date":
                continue
            value = _numeric(raw)
            if value is not None:
                output.setdefault(column.strip(), []).append({"date": day, "value": value})
    return {column: _dedupe(points) for column, points in output.items()}


def parse_fed_ddp_csv(text: str) -> dict[str, list[dict]]:
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.lstrip('"').startswith("Time Period")), None)
    if start is None:
        raise SourceError("Federal Reserve DDP: no se encontró Time Period")
    output: dict[str, list[dict]] = {}
    for row in csv.DictReader(io.StringIO("\n".join(lines[start:]))):
        day = _iso_day(row.get("Time Period") or "")
        if not day:
            continue
        for column, raw in row.items():
            if column == "Time Period":
                continue
            value = _numeric(raw)
            if value is not None:
                output.setdefault(column.strip(), []).append({"date": day, "value": value})
    return {column: _dedupe(points) for column, points in output.items()}


def parse_fred_bundle_csv(text: str) -> dict[str, list[dict]]:
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    if not reader.fieldnames:
        raise SourceError("FRED: CSV sin cabecera")
    date_column = next((column for column in ("observation_date", "DATE") if column in reader.fieldnames), None)
    if date_column is None:
        raise SourceError(f"FRED: columna de fecha no reconocida: {reader.fieldnames}")
    output: dict[str, list[dict]] = {
        column: [] for column in reader.fieldnames if column != date_column
    }
    for row in reader:
        day = _iso_day(row.get(date_column) or "")
        if not day:
            continue
        for series_id in output:
            value = _numeric(row.get(series_id))
            if value is not None:
                output[series_id].append({"date": day, "value": value})
    return {series_id: _dedupe(points) for series_id, points in output.items()}


def parse_sofr_json(payload: dict) -> list[dict]:
    points = []
    for row in payload.get("refRates", []):
        value = _numeric(row.get("percentRate"))
        day = _iso_day(row.get("effectiveDate") or "")
        if value is not None and day:
            points.append({"date": day, "value": value})
    return _dedupe(points)


def parse_rrp_json(payload: dict) -> list[dict]:
    by_day: dict[str, float] = {}
    for row in payload.get("repo", {}).get("operations", []):
        note = str(row.get("note") or "").lower()
        if "small value" in note or "exercise" in note:
            continue
        day = _iso_day(row.get("operationDate") or "")
        value = _numeric(row.get("totalAmtAccepted"))
        if day and value is not None:
            by_day[day] = by_day.get(day, 0.0) + value / 1_000_000_000
    return [{"date": day, "value": value} for day, value in sorted(by_day.items())]


def parse_sdmx_csv(text: str) -> list[dict]:
    lines = [line for line in text.splitlines() if line.strip()]
    start = next(
        (i for i, line in enumerate(lines) if "TIME_PERIOD" in line.upper() and "OBS_VALUE" in line.upper()),
        None,
    )
    if start is None:
        raise SourceError("SDMX CSV: no se encontraron TIME_PERIOD y OBS_VALUE")
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


def parse_mof_csv(text: str) -> list[dict]:
    lines = [line for line in text.splitlines() if line.strip()]
    start = None
    for index, line in enumerate(lines):
        cells = next(csv.reader([line]))
        normalized_cells = {re.sub(r"[^0-9a-z年基準日]", "", cell.lower()) for cell in cells}
        has_date = bool(normalized_cells & {"date", "基準日"})
        has_ten = bool(normalized_cells & {"10y", "10yr", "10year", "10years", "10年"})
        if has_date and has_ten:
            start = index
            break
    if start is None:
        raise SourceError("MOF Japan: no se reconoció la fila de cabecera")
    reader = csv.DictReader(io.StringIO("\n".join(lines[start:])))
    if not reader.fieldnames:
        raise SourceError("MOF Japan: CSV sin cabecera")
    normalized = {re.sub(r"[^0-9a-z年]", "", name.lower()): name for name in reader.fieldnames}
    date_column = next((name for key, name in normalized.items() if key in {"date", "基準日"}), reader.fieldnames[0])
    value_column = next(
        (name for key, name in normalized.items() if key in {"10y", "10yr", "10year", "10years", "10年"}),
        None,
    )
    if value_column is None:
        raise SourceError(f"MOF Japan: no se reconoció la columna 10 años: {reader.fieldnames}")
    points = []
    for row in reader:
        day = _iso_day(row.get(date_column) or "")
        value = _numeric(row.get(value_column))
        if day and value is not None:
            points.append({"date": day, "value": value})
    return _dedupe(points)


def parse_boe_csv(text: str, series_code: str = "IUDMNPY") -> list[dict]:
    lines = [line for line in text.splitlines() if line.strip()]
    start = next((i for i, line in enumerate(lines) if series_code.upper() in line.upper()), None)
    if start is None:
        raise SourceError(f"Bank of England: no se encontró {series_code}")
    points = []
    for row in csv.DictReader(io.StringIO("\n".join(lines[start:]))):
        normalized = {str(key).strip().upper(): value for key, value in row.items() if key}
        day = _iso_day(normalized.get("DATE") or normalized.get("TIME") or "")
        value = _numeric(normalized.get(series_code.upper()))
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


def _html_rows(text: str) -> list[list[str]]:
    parser = _TableParser()
    parser.feed(text)
    return parser.rows


def parse_norges_html(text: str) -> list[dict]:
    points = []
    for row in _html_rows(text):
        if len(row) < 8:
            continue
        day = _iso_day(row[0])
        value = _numeric(row[7])
        if day and value is not None:
            points.append({"date": day, "value": value})
    if not points:
        raise SourceError("Norges Bank: no se reconoció la tabla de tipos genéricos")
    return _dedupe(points)


def parse_h41_html(text: str) -> dict[str, list[dict]]:
    stripped = re.sub(r"<[^>]+>", " ", text)
    observation = re.search(
        r"Wednesday\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})",
        stripped,
        flags=re.I,
    )
    release = re.search(r"Release Date:\s*</?[^>]*>*\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})", text, flags=re.I)
    if release is None:
        release = re.search(r"Release Date:\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})", stripped, flags=re.I)
    day = _iso_day(observation.group(1)) if observation else _iso_day(release.group(1)) if release else None
    if not day:
        raise SourceError("H.4.1: no se reconoció la fecha de observación")

    targets = {
        "total assets": "WALCL",
        "u.s. treasury, general account": "WTREGEN",
    }
    output: dict[str, list[dict]] = {}
    for row in _html_rows(text):
        if not row:
            continue
        label = " ".join(row[0].lower().split())
        series_id = targets.get(label)
        if not series_id:
            continue
        values = [_numeric(cell) for cell in row[1:]]
        # La primera cifra no nula es el nivel de la columna Wednesday; las
        # celdas de eliminación aparecen como (0) y se ignoran.
        value = next((number for number in values if number is not None and number > 0), None)
        if value is not None:
            output[series_id] = [{"date": day, "value": value}]
    missing = sorted(set(targets.values()) - set(output))
    if missing:
        raise SourceError(f"H.4.1: filas no reconocidas: {', '.join(missing)}")
    return output


def parse_bls_json(payload: dict) -> dict[str, list[dict]]:
    if payload.get("status") not in {None, "REQUEST_SUCCEEDED"}:
        raise SourceError(f"BLS: {payload.get('message') or payload.get('status')}")
    output: dict[str, list[dict]] = {}
    for series in payload.get("Results", {}).get("series", []):
        points = []
        for row in series.get("data", []):
            period = str(row.get("period") or "")
            if not re.fullmatch(r"M(0[1-9]|1[0-2])", period):
                continue
            day = f"{row.get('year')}-{period[1:]}-01"
            value = _numeric(row.get("value"))
            if value is not None:
                points.append({"date": day, "value": value})
        output[series.get("seriesID")] = _dedupe(points)
    return output


def parse_eia_json(payload: dict) -> list[dict]:
    error = payload.get("error")
    if error:
        raise SourceError(f"EIA: {error}")
    points = []
    for row in payload.get("response", {}).get("data", []):
        day = _iso_day(row.get("period") or "")
        value = _numeric(row.get("value"))
        if day and value is not None:
            points.append({"date": day, "value": value})
    return _dedupe(points)


def parse_bea_nipa(payload: dict, description: str) -> list[dict]:
    results = payload.get("BEAAPI", {}).get("Results", {})
    if isinstance(results, dict) and results.get("Error"):
        raise SourceError(f"BEA: {results['Error']}")
    rows = results.get("Data", []) if isinstance(results, dict) else []
    needle = description.casefold()
    candidates = [
        row for row in rows
        if needle in str(row.get("LineDescription") or "").casefold()
    ]
    if not candidates:
        raise SourceError(f"BEA: no se encontró la línea {description}")
    line_number = candidates[0].get("LineNumber")
    points = []
    for row in candidates:
        if row.get("LineNumber") != line_number:
            continue
        day = _iso_day(row.get("TimePeriod") or "")
        value = _numeric(row.get("DataValue"))
        if day and value is not None:
            points.append({"date": day, "value": value})
    return _dedupe(points)


def parse_dbnomics_json(payload: dict, divisor: float = 1.0) -> list[dict]:
    docs = payload.get("series", {}).get("docs", [])
    if not docs:
        raise SourceError("DBnomics: respuesta sin series")
    points = []
    for period, raw in zip(docs[0].get("period", []), docs[0].get("value", [])):
        day = _iso_day(period)
        value = _numeric(raw)
        if day and value is not None:
            points.append({"date": day, "value": value / divisor})
    return _dedupe(points)


CAPEX_COMPANY_IDS = {
    "microsoft": "CAPEX_MSFT",
    "alphabet": "CAPEX_GOOG",
    "amazon": "CAPEX_AMZN",
    "meta": "CAPEX_META",
    "oracle": "CAPEX_ORCL",
}


def parse_capex_tracker_csv(text: str) -> dict[str, list[dict]]:
    """Lee el dataset CC BY y conserva el valor sobre la base declarada.

    ``headline_usd`` no se fuerza a una definición contable común: el dataset
    elige la magnitud que cada compañía utiliza en su guía y documenta la base
    y las fuentes primarias en cada fila. El panel lo presenta como una cesta
    descriptiva, no como una suma contable homogénea.
    """
    lines = [line for line in text.splitlines() if line.strip() and not line.startswith("#")]
    if not lines:
        raise SourceError("Hyperscaler Capex Tracker: CSV vacío")
    output: dict[str, list[dict]] = {series_id: [] for series_id in CAPEX_COMPANY_IDS.values()}
    for row in csv.DictReader(io.StringIO("\n".join(lines))):
        series_id = CAPEX_COMPANY_IDS.get(str(row.get("company") or "").strip().lower())
        day = _iso_day(row.get("period_end") or "")
        value = _numeric(row.get("headline_usd"))
        if series_id and day and value is not None:
            output[series_id].append({"date": day, "value": value / 1_000_000_000})
    return {series_id: _dedupe(points) for series_id, points in output.items()}


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
        return {column: _dedupe(points) for column, points in merged.items()}
    return _memo(f"treasury:{kind}", load)


FED_PACKAGES = {
    "indexes": "122e3bcb627e8e53f1bf72a1a09cfb81",
    "rates": "60f32914ab61dfab590e0e470153e3ae",
    "policy": "c27939ee810cb2e929a920a6bd77d9f6",
}


def _fed_package(release: str, package: str, observations: int = 500) -> dict[str, list[dict]]:
    def load():
        series = FED_PACKAGES[package]
        url = (
            "https://www.federalreserve.gov/datadownload/Output.aspx?"
            f"rel={release}&series={series}&lastobs={observations}"
            "&filetype=csv&label=include&layout=seriescolumn"
        )
        # Data Download puede responder HTTP 200 con cuerpo vacio durante
        # episodios breves de carga. ``_read`` no puede distinguir ese caso
        # de una descarga valida, de modo que el adaptador reintenta tambien
        # los errores de contenido y nunca convierte el vacio en cero.
        last_error: SourceError | None = None
        for attempt in range(3):
            try:
                return parse_fed_ddp_csv(_text(url))
            except SourceError as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(1.25 * (attempt + 1))
        raise last_error or SourceError("Federal Reserve DDP: respuesta vacia")
    return _memo(f"fed:{release}:{package}", load)


def _sofr() -> list[dict]:
    return _memo(
        "nyfed:sofr",
        lambda: parse_sofr_json(_json("https://markets.newyorkfed.org/api/rates/secured/sofr/last/500.json")),
    )


def _rrp() -> list[dict]:
    def load():
        end = date.today()
        start = end - timedelta(days=400)
        url = (
            "https://markets.newyorkfed.org/api/rp/reverserepo/propositions/search.json?"
            + urlencode({"startDate": start.isoformat(), "endDate": end.isoformat()})
        )
        return parse_rrp_json(_json(url))
    return _memo("nyfed:rrp", load)


def _h41() -> dict[str, list[dict]]:
    return _memo(
        "fed:h41-current",
        lambda: parse_h41_html(_text("https://www.federalreserve.gov/releases/h41/current/h41.htm")),
    )


def _fiscal_debt_package() -> dict[str, list[dict]]:
    def load():
        url = (
            "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/"
            "accounting/od/debt_to_penny?sort=-record_date&page%5Bsize%5D=500"
        )
        output = {"GFDEBTN": [], "US_DEBT_HELD_PUBLIC": []}
        for row in _json(url).get("data", []):
            total = _numeric(row.get("tot_pub_debt_out_amt"))
            public = _numeric(row.get("debt_held_public_amt"))
            if total is not None:
                output["GFDEBTN"].append({"date": row["record_date"], "value": total / 1_000_000})
            if public is not None:
                output["US_DEBT_HELD_PUBLIC"].append({"date": row["record_date"], "value": public / 1_000_000})
        return {series_id: _dedupe(points) for series_id, points in output.items()}
    return _memo("fiscal:debt", load)


FRED_MARKET_IDS = ("SP500", "BAMLC0A0CM", "BAMLC0A0CMEY")


def _fred_market_package() -> dict[str, list[dict]]:
    def load():
        query = urlencode({"id": ",".join(FRED_MARKET_IDS)})
        return parse_fred_bundle_csv(_text(f"https://fred.stlouisfed.org/graph/fredgraph.csv?{query}"))
    return _memo("fred:market-context", load)


def _gold() -> list[dict]:
    def load():
        payload = None
        last_error = None
        for attempt in range(3):
            try:
                url = f"https://prices.lbma.org.uk/json/gold_am.json?cache={int(time.time())}-{attempt}"
                raw = _read(url, headers={
                    "Accept": "application/json,text/plain,*/*",
                    "Referer": "https://www.lbma.org.uk/prices-and-data/precious-metal-prices",
                })
                payload = json.loads(raw.decode("utf-8-sig", errors="replace"))
                break
            except (SourceError, json.JSONDecodeError) as exc:
                last_error = exc
                time.sleep(1.5 * (attempt + 1))
        if not isinstance(payload, list):
            raise SourceError(f"LBMA: respuesta no interpretable: {last_error}")
        points = []
        for row in payload:
            values = row.get("v") or []
            value = _numeric(values[0] if values else None)
            if value is not None:
                points.append({"date": row["d"], "value": value})
        return _dedupe(points)[-900:]
    return _memo("lbma:gold-am", load)


def _bitcoin() -> list[dict]:
    def load():
        payload = _json(
            "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?"
            "vs_currency=usd&days=365&interval=daily"
        )
        points = []
        for timestamp_ms, raw in payload.get("prices", []):
            day = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).date().isoformat()
            value = _numeric(raw)
            if value is not None:
                points.append({"date": day, "value": value})
        return _dedupe(points)
    return _memo("coingecko:btc", load)


def _vix() -> list[dict]:
    def load():
        points = []
        text = _text("https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv")
        for row in csv.DictReader(io.StringIO(text)):
            day = _iso_day(row.get("DATE") or "")
            value = _numeric(row.get("CLOSE"))
            if day and value is not None:
                points.append({"date": day, "value": value})
        return _dedupe(points)[-900:]
    return _memo("cboe:vix", load)


def _bls() -> dict[str, list[dict]]:
    def load():
        payload = json.dumps({
            "seriesid": ["CUSR0000SA0", "LNS14000000"],
            "startyear": str(date.today().year - 3),
            "endyear": str(date.today().year),
        }).encode("utf-8")
        return parse_bls_json(_json(
            "https://api.bls.gov/publicAPI/v2/timeseries/data/",
            data=payload,
            headers={"Content-Type": "application/json"},
        ))
    return _memo("bls:macro", load)


def _eia(route: str, series: str) -> list[dict]:
    def load():
        start = (date.today() - timedelta(days=500)).isoformat()
        query = (
            "api_key=DEMO_KEY&frequency=daily&data[0]=value"
            f"&facets[series][]={series}&start={start}"
            "&sort[0][column]=period&sort[0][direction]=asc&offset=0&length=5000"
        )
        return parse_eia_json(_json(f"https://api.eia.gov/v2/{route}/data/?{query}"))
    return _memo(f"eia:{route}:{series}", load)


def _japan_10y() -> list[dict]:
    def decode(raw: bytes) -> list[dict]:
        for encoding in ("utf-8-sig", "cp932", "shift_jis"):
            try:
                points = parse_mof_csv(raw.decode(encoding))
                if points:
                    return points
            except (UnicodeDecodeError, SourceError):
                continue
        raise SourceError("MOF Japan: no se pudo decodificar o interpretar el CSV")

    def load():
        base = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/"
        # El fichero corriente solo contiene el mes abierto. Se une con el
        # historico oficial para que la ventana de 92 dias sea evaluable.
        historical = decode(_read(base + "historical/jgbcme_all.csv"))
        current = decode(_read(base + "jgbcme.csv"))
        return _dedupe(historical + current)
    return _memo("mof:jgb-10y", load)


def _germany_10y() -> list[dict]:
    def load():
        start = (date.today() - timedelta(days=500)).isoformat()
        query = urlencode({"format": "sdmx_csv", "lang": "en", "startPeriod": start})
        return parse_sdmx_csv(_text(
            "https://api.statistiken.bundesbank.de/rest/data/BBSSY/"
            "D.REN.EUR.A630.000000WT1010.A?" + query
        ))
    return _memo("bundesbank:bund-10y", load)


def _uk_10y() -> list[dict]:
    def load():
        start = f"01/Jan/{date.today().year - 2}"
        query = urlencode({
            "csv.x": "yes",
            "Datefrom": start,
            "Dateto": "now",
            "SeriesCodes": "IUDMNPY",
            "CSVF": "TN",
            "UsingCodes": "Y",
            "VPD": "Y",
            "VFD": "N",
        })
        return parse_boe_csv(_text(
            "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?" + query
        ), "IUDMNPY")
    return _memo("boe:gilt-10y", load)


def _norway_10y() -> list[dict]:
    return _memo(
        "norges:govt-10y",
        lambda: parse_norges_html(_text(
            "https://www.norges-bank.no/en/topics/Statistics/"
            "norwegian-government-securities/generiske-statsrenter/"
        )),
    )


def _euro_area_10y() -> list[dict]:
    def load():
        start = (date.today() - timedelta(days=500)).isoformat()
        url = (
            "https://data-api.ecb.europa.eu/service/data/YC/"
            "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y?"
            + urlencode({"format": "csvdata", "startPeriod": start})
        )
        return parse_sdmx_csv(_text(url))
    return _memo("ecb:euro-aaa-10y", load)


def _bea(table: str, series_code: str) -> list[dict]:
    """Datos BEA transportados por el espejo abierto de DBnomics.

    La API directa de BEA exige una clave personal. DBnomics replica las tablas
    NIPA sin alterar periodos y permite mantener el robot sin secretos; la
    procedencia se declara expresamente en el catálogo. Las tablas descargadas
    vienen en millones de dólares y se normalizan a miles de millones.
    """
    return _memo(
        f"dbnomics:bea:{table}:{series_code}",
        lambda: parse_dbnomics_json(
            _json(f"https://api.db.nomics.world/v22/series/BEA/NIPA-{table}/{series_code}?observations=1"),
            divisor=1_000,
        ),
    )


def _capex_package() -> dict[str, list[dict]]:
    def load():
        return parse_capex_tracker_csv(_text("https://www.regardsofwallstreet.com/data/capex.csv"))
    return _memo("capex:hyperscaler-tracker", load)


def _capex(series_id: str) -> list[dict]:
    return _capex_package().get(series_id, [])


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
        points = _fed_package("H10", "indexes").get("JRXWTFB_N.B", [])
    elif series_id in H10_RATES_MAP:
        points = _fed_package("H10", "rates").get(H10_RATES_MAP[series_id], [])
    elif series_id == "SOFR":
        points = _sofr()
    elif series_id == "IORB":
        points = _fed_package("PRATES", "policy", 900).get("RESBM_N.D", [])
    elif series_id == "RRPONTSYD":
        points = _rrp()
    elif series_id in {"WALCL", "WTREGEN"}:
        points = _h41().get(series_id, [])
    elif series_id in {"GFDEBTN", "US_DEBT_HELD_PUBLIC"}:
        points = _fiscal_debt_package().get(series_id, [])
    elif series_id == "GOLDAMGBD228NLBM":
        points = _gold()
    elif series_id == "CBBTCUSD":
        points = _bitcoin()
    elif series_id == "VIXCLS":
        points = _vix()
    elif series_id in FRED_MARKET_IDS:
        points = _fred_market_package().get(series_id, [])
    elif series_id == "CPIAUCSL":
        points = _bls().get("CUSR0000SA0", [])
    elif series_id == "UNRATE":
        points = _bls().get("LNS14000000", [])
    elif series_id == "DCOILBRENTEU":
        points = _eia("petroleum/pri/spt", "RBRTE")
    elif series_id == "DHHNGSP":
        points = _eia("natural-gas/pri/fut", "RNGWHHD")
    elif series_id == "IRLTLT01JPM156N":
        points = _japan_10y()
    elif series_id == "IRLTLT01DEM156N":
        points = _germany_10y()
    elif series_id == "IRLTLT01GBM156N":
        points = _uk_10y()
    elif series_id == "IRLTLT01NOM156N":
        points = _norway_10y()
    elif series_id == "IRLTLT01EZM156N":
        points = _euro_area_10y()
    elif series_id == "GDP":
        points = _bea("T10105", "A191RC-Q")
    elif series_id == "A091RC1Q027SBEA":
        points = _bea("T30200", "A091RC-Q")
    elif series_id in CAPEX_COMPANY_IDS.values():
        points = _capex(series_id)
    else:
        raise SourceError(f"{series_id}: fuente no incorporada")

    points = _dedupe(points)
    if not points:
        raise SourceError(f"{series_id}: la fuente respondió sin observaciones")
    return points


CORE_SERIES = frozenset({
    "DGS2", "DGS10", "DGS30", "DFII10", "T10YIE",
    "DTWEXBGS", "DEXUSEU", "DEXNOUS", "DEXJPUS", "DEXCHUS", "SOFR",
})
