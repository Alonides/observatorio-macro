"""Cliente pequeño y tolerante a fallos para el CSV público de FRED."""

from __future__ import annotations

import csv
import io
import time
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"


class SourceError(RuntimeError):
    pass


def parse_fred_csv(text: str, series_id: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    if not reader.fieldnames:
        raise SourceError(f"{series_id}: CSV sin cabecera")
    date_column = next((c for c in ("DATE", "observation_date") if c in reader.fieldnames), None)
    value_column = series_id if series_id in reader.fieldnames else next(
        (c for c in reader.fieldnames if c != date_column), None
    )
    if not date_column or not value_column:
        raise SourceError(f"{series_id}: columnas no reconocidas: {reader.fieldnames}")

    points: list[dict] = []
    for row in reader:
        raw = (row.get(value_column) or "").strip()
        raw_date = (row.get(date_column) or "").strip()
        if raw in {"", ".", "NA", "N/A"} or not raw_date:
            continue
        try:
            date.fromisoformat(raw_date)
            value = float(raw)
        except ValueError:
            continue
        points.append({"date": raw_date, "value": value})
    if not points:
        raise SourceError(f"{series_id}: no contiene observaciones numéricas")
    return points


def fetch_series(series_id: str, opener=urlopen, retries: int = 3) -> list[dict]:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = Request(
                FRED_CSV.format(series_id=series_id),
                headers={"User-Agent": "observatorio-macro/0.1"},
            )
            with opener(request, timeout=45) as response:
                text = response.read().decode("utf-8-sig")
            return parse_fred_csv(text, series_id)
        except (HTTPError, URLError, TimeoutError, SourceError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    raise SourceError(f"{series_id}: {last_error}")
