"""Flexible but bounded parser for public dated-price JSON payloads.

The parser accepts only structures that preserve an explicit date/value
relationship:

* objects with date and price fields;
* two-element [date, value] rows;
* mappings whose keys are dates and values are numeric;
* parallel date and value arrays of equal length.

It deliberately does not infer dates from array position or scrape display text.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from math import isfinite
from typing import Mapping, Sequence

from ..official import SourceError


DATE_KEYS = (
    "date", "period", "day", "time", "timestamp", "datetime", "t",
    "asof", "as_of", "asOf", "updated", "updated_at",
)
VALUE_KEYS = (
    "close", "price", "priceUsd", "priceUSD", "price_usd", "value",
    "settle", "settlement", "brent", "c", "last", "last_price",
    "current", "usd_per_barrel",
)
DATE_ARRAY_KEYS = ("dates", "periods", "days", "timestamps", "times", "labels")
VALUE_ARRAY_KEYS = (
    "values", "prices", "pricesUsd", "pricesUSD", "prices_usd",
    "closes", "close", "settles", "data",
)


def _parse_date(raw) -> date | None:
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        try:
            value = float(raw)
            if value < 100_000_000:
                return None
            if value > 1e12:
                value /= 1000.0
            return datetime.fromtimestamp(value, tz=timezone.utc).date()
        except (OSError, OverflowError, ValueError):
            return None
    text = str(raw).strip()
    if not text:
        return None
    if text.isdigit():
        return _parse_date(float(text))
    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        pass
    for fmt in (
        "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y",
        "%d %b %Y", "%b %d, %Y", "%B %d, %Y",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _parse_value(raw) -> float | None:
    if raw is None or isinstance(raw, bool) or isinstance(raw, (Mapping, list, tuple)):
        return None
    try:
        value = float(str(raw).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return value if isfinite(value) and value > 0.0 else None


def _is_explicit_date_token(raw) -> bool:
    if isinstance(raw, date):
        return True
    if isinstance(raw, bool) or raw is None:
        return False
    if isinstance(raw, (int, float)):
        try:
            return float(raw) >= 100_000_000
        except (TypeError, ValueError):
            return False
    text = str(raw).strip()
    if not text:
        return False
    if text.isdigit():
        try:
            return float(text) >= 100_000_000
        except ValueError:
            return False
    lowered = text.lower()
    month_tokens = (
        "jan", "feb", "mar", "apr", "may", "jun",
        "jul", "aug", "sep", "oct", "nov", "dec",
    )
    return any(token in text for token in ("-", "/", "T", ":")) or any(
        month in lowered for month in month_tokens
    )


def _first_parsed(mapping: Mapping[str, object], keys: Sequence[str], parser):
    for key in keys:
        if key not in mapping:
            continue
        parsed = parser(mapping.get(key))
        if parsed is not None:
            return parsed
    return None


def _parallel_arrays(node: Mapping[str, object], output: dict[date, float]) -> None:
    for date_key in DATE_ARRAY_KEYS:
        dates = node.get(date_key)
        if not isinstance(dates, (list, tuple)):
            continue
        for value_key in VALUE_ARRAY_KEYS:
            values = node.get(value_key)
            if not isinstance(values, (list, tuple)) or len(values) != len(dates):
                continue
            for raw_day, raw_value in zip(dates, values):
                day = _parse_date(raw_day)
                value = _parse_value(raw_value)
                if day is not None and value is not None:
                    output[day] = value


def _extract(node, output: dict[date, float]) -> None:
    if isinstance(node, Mapping):
        day = _first_parsed(node, DATE_KEYS, _parse_date)
        value = _first_parsed(node, VALUE_KEYS, _parse_value)
        if day is not None and value is not None:
            output[day] = value

        _parallel_arrays(node, output)

        for raw_key, raw_value in node.items():
            keyed_day = _parse_date(raw_key)
            keyed_value = _parse_value(raw_value)
            if keyed_day is not None and keyed_value is not None:
                output[keyed_day] = keyed_value

        for child in node.values():
            if isinstance(child, (Mapping, list, tuple)):
                _extract(child, output)
        return

    if isinstance(node, (list, tuple)):
        if len(node) >= 2 and _is_explicit_date_token(node[0]):
            day = _parse_date(node[0])
            value = _parse_value(node[1])
            if day is not None and value is not None:
                output[day] = value
        for child in node:
            if isinstance(child, (Mapping, list, tuple)):
                _extract(child, output)


def _shape_summary(node, depth: int = 0):
    """Return field names and container types only; never emit payload values."""
    if depth >= 2:
        return type(node).__name__
    if isinstance(node, Mapping):
        summary = {}
        for key, value in list(node.items())[:12]:
            if isinstance(value, Mapping):
                summary[str(key)] = {
                    "type": "object",
                    "keys": [str(item) for item in list(value.keys())[:12]],
                }
            elif isinstance(value, (list, tuple)):
                first = value[0] if value else None
                if isinstance(first, Mapping):
                    first_shape = {
                        "type": "object",
                        "keys": [str(item) for item in list(first.keys())[:12]],
                    }
                elif isinstance(first, (list, tuple)):
                    first_shape = {"type": type(first).__name__, "length": len(first)}
                else:
                    first_shape = type(first).__name__ if first is not None else "empty"
                summary[str(key)] = {
                    "type": type(value).__name__,
                    "length": len(value),
                    "first": first_shape,
                }
            else:
                summary[str(key)] = type(value).__name__
        return summary
    if isinstance(node, (list, tuple)):
        first = node[0] if node else None
        return {
            "type": type(node).__name__,
            "length": len(node),
            "first": _shape_summary(first, depth + 1) if first is not None else "empty",
        }
    return type(node).__name__


def parse_dated_price_payload(payload: Mapping[str, object] | Sequence[object]) -> list[dict]:
    output: dict[date, float] = {}
    _extract(payload, output)
    if not output:
        raise SourceError(
            "public price payload contained no explicit dated values; "
            f"shape={_shape_summary(payload)}"
        )
    return [
        {"date": day.isoformat(), "value": output[day]}
        for day in sorted(output)
    ]


__all__ = ["parse_dated_price_payload"]
