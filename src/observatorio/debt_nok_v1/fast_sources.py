"""Primary-source proxy loaders for the Debt/NOK provisional fast lane.

ECB reference rates provide the FX extensions. Oil uses a two-part proxy:
long WTI spot history from the U.S. EIA for overlap validation and a short
recent tail of delayed CME WTI settlements. CME values are return-spliced to
the last EIA WTI spot level and are treated as reference data, never as an
official Brent observation.
"""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from math import isfinite
from typing import Callable, Mapping, Sequence
from urllib.parse import urlencode

from ..official import SourceError, _eia, _read
from .fast_bridge import ECB_REFERENCE_URL, parse_ecb_reference_xml


EIA_WTI_ROUTE = "petroleum/pri/spt"
EIA_WTI_SERIES = "RWTC"
CME_WTI_PRODUCT_ID = "425"
CME_WTI_SETTLEMENT_URL = (
    "https://www.cmegroup.com/CmeWS/mvc/Settlements/Futures/Settlements/"
    f"{CME_WTI_PRODUCT_ID}/FUT"
)
CME_WTI_REFERER = (
    "https://www.cmegroup.com/markets/energy/crude-oil/"
    "light-sweet-crude.settlements.html"
)
CME_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Referer": CME_WTI_REFERER,
}


def _number(raw) -> float | None:
    if raw is None:
        return None
    text = str(raw).strip().replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        value = float(match.group(0))
    except ValueError:
        return None
    return value if isfinite(value) and value > 0.0 else None


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


def _points(values: Mapping[date, float]) -> list[dict]:
    return [
        {"date": day.isoformat(), "value": value}
        for day, value in sorted(values.items())
    ]


def _business_day_lag(start: date, end: date) -> int:
    if start >= end:
        return 0
    current = start + timedelta(days=1)
    lag = 0
    while current <= end:
        if current.weekday() < 5:
            lag += 1
        current += timedelta(days=1)
    return lag


def parse_cme_wti_settlement(payload: Mapping[str, object], trade_day: date) -> dict | None:
    """Return the front valid WTI settlement for one CME trade date."""
    rows = payload.get("settlements")
    if not isinstance(rows, list):
        return None
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        month = str(row.get("month") or "").strip()
        if not month or month.lower() in {"total", "volume", "open interest"}:
            continue
        value = _number(row.get("settle"))
        if value is None:
            continue
        return {
            "date": trade_day.isoformat(),
            "value": value,
            "contract": month,
            "updated": row.get("updated") or payload.get("updateTime"),
        }
    return None


def fetch_recent_cme_wti_settlements(
    read_bytes: Callable[..., bytes] = _read,
    today: date | None = None,
    target_sessions: int = 10,
    calendar_lookback: int = 18,
) -> tuple[list[dict], dict]:
    """Fetch a small delayed/reference settlement window from CME.

    Individual missing dates are normal: weekends, holidays and unpublished
    current-day settlements are skipped. A total source failure raises only
    after the full short window has been attempted.
    """
    today = today or date.today()
    collected: dict[date, dict] = {}
    attempts = 0
    failures: list[str] = []
    for offset in range(calendar_lookback + 1):
        trade_day = today - timedelta(days=offset)
        if trade_day.weekday() >= 5:
            continue
        query = urlencode({"tradeDate": trade_day.strftime("%m/%d/%Y")})
        url = f"{CME_WTI_SETTLEMENT_URL}?{query}"
        attempts += 1
        try:
            payload = json.loads(
                read_bytes(
                    url,
                    timeout=6,
                    retries=1,
                    headers=CME_BROWSER_HEADERS,
                ).decode("utf-8-sig", errors="replace")
            )
            point = parse_cme_wti_settlement(payload, trade_day)
            if point:
                collected[trade_day] = point
        except Exception as exc:
            failures.append(f"{trade_day.isoformat()}: {exc}")
        if len(collected) >= target_sessions:
            break

    if not collected:
        detail = failures[-1] if failures else "no numeric settlement rows"
        raise SourceError(f"CME WTI settlements unavailable: {detail}")
    points = [collected[day] for day in sorted(collected)]
    return points, {
        "attempts": attempts,
        "observations": len(points),
        "start": points[0]["date"],
        "end": points[-1]["date"],
        "contracts": sorted({str(point.get("contract")) for point in points if point.get("contract")}),
        "failed_dates": len(failures),
        "reference_only": True,
    }


def build_eia_cme_wti_proxy(
    eia_spot_points: Sequence[Mapping[str, object]],
    cme_settlement_points: Sequence[Mapping[str, object]],
    maximum_anchor_gap_days: int = 2,
) -> tuple[list[dict], dict]:
    """Append scaled CME returns beyond the last EIA WTI spot observation."""
    eia = _point_map(eia_spot_points)
    cme = _point_map(cme_settlement_points)
    if not eia:
        raise SourceError("EIA WTI spot history is empty")
    if not cme:
        raise SourceError("CME WTI settlement tail is empty")

    eia_last = max(eia)
    cme_candidates = [day for day in cme if day <= eia_last]
    if not cme_candidates:
        raise SourceError("CME tail has no anchor on or before the last EIA WTI date")
    cme_anchor = max(cme_candidates)
    anchor_gap = _business_day_lag(cme_anchor, eia_last)
    if anchor_gap > maximum_anchor_gap_days:
        raise SourceError(
            f"CME/EIA WTI anchor gap is {anchor_gap} business days; "
            f"maximum is {maximum_anchor_gap_days}"
        )

    scale = eia[eia_last] / cme[cme_anchor]
    output = dict(eia)
    appended: list[dict] = []
    for day in sorted(cme):
        if day <= eia_last:
            continue
        value = cme[day] * scale
        if isfinite(value) and value > 0.0:
            output[day] = value
            appended.append({"date": day.isoformat(), "value": value})

    return _points(output), {
        "eia_last": eia_last.isoformat(),
        "cme_anchor": cme_anchor.isoformat(),
        "anchor_gap_business_days": anchor_gap,
        "scale": round(scale, 8),
        "appended_observations": len(appended),
        "bridge_start": appended[0]["date"] if appended else None,
        "bridge_end": appended[-1]["date"] if appended else None,
        "method": "CME settlement returns scaled to the last EIA WTI spot level",
    }


def _latest(points: Sequence[Mapping[str, object]]) -> str | None:
    values = _point_map(points)
    return max(values).isoformat() if values else None


def fetch_primary_fast_proxies(
    read_bytes: Callable[..., bytes] = _read,
    eia_fetcher: Callable[[str, str], list[dict]] = _eia,
    today: date | None = None,
) -> tuple[dict[str, list[dict]], dict, dict[str, str]]:
    """Fetch ECB FX proxies and the EIA+CME hybrid WTI proxy."""
    proxies: dict[str, list[dict]] = {}
    sources: dict[str, dict] = {}
    errors: dict[str, str] = {}

    try:
        xml = read_bytes(ECB_REFERENCE_URL).decode("utf-8-sig", errors="replace")
        ecb = parse_ecb_reference_xml(xml)
        proxies.update(ecb)
        sources["ECB_REFERENCE"] = {
            "provider": "European Central Bank",
            "url": ECB_REFERENCE_URL,
            "status": "ok",
            "latest": max(filter(None, (_latest(points) for points in ecb.values())), default=None),
            "observations": {key: len(value) for key, value in ecb.items()},
            "role": "official reference-rate proxy",
        }
    except Exception as exc:
        errors["ECB_REFERENCE"] = str(exc)
        sources["ECB_REFERENCE"] = {
            "provider": "European Central Bank",
            "url": ECB_REFERENCE_URL,
            "status": "error",
        }

    eia_spot: list[dict] = []
    try:
        eia_spot = eia_fetcher(EIA_WTI_ROUTE, EIA_WTI_SERIES)
        if not eia_spot:
            raise SourceError("EIA WTI spot returned no observations")
        sources["EIA_WTI_SPOT"] = {
            "provider": "U.S. Energy Information Administration",
            "url": "https://api.eia.gov/v2/petroleum/pri/spt/",
            "series": EIA_WTI_SERIES,
            "status": "ok",
            "latest": _latest(eia_spot),
            "observations": len(eia_spot),
            "role": "long official overlap history for oil proxy validation",
        }
    except Exception as exc:
        errors["EIA_WTI_SPOT"] = str(exc)
        sources["EIA_WTI_SPOT"] = {
            "provider": "U.S. Energy Information Administration",
            "url": "https://api.eia.gov/v2/petroleum/pri/spt/",
            "series": EIA_WTI_SERIES,
            "status": "error",
        }

    cme_points: list[dict] = []
    cme_meta: dict = {}
    try:
        cme_points, cme_meta = fetch_recent_cme_wti_settlements(
            read_bytes=read_bytes,
            today=today,
        )
        sources["CME_WTI_SETTLEMENT"] = {
            "provider": "CME Group",
            "url": CME_WTI_SETTLEMENT_URL,
            "product_id": CME_WTI_PRODUCT_ID,
            "status": "ok",
            "latest": _latest(cme_points),
            "observations": len(cme_points),
            "role": "delayed/reference recent settlement tail",
            **cme_meta,
        }
    except Exception as exc:
        errors["CME_WTI_SETTLEMENT"] = str(exc)
        sources["CME_WTI_SETTLEMENT"] = {
            "provider": "CME Group",
            "url": CME_WTI_SETTLEMENT_URL,
            "product_id": CME_WTI_PRODUCT_ID,
            "status": "error",
            "reference_only": True,
        }

    if eia_spot and cme_points:
        try:
            hybrid, hybrid_meta = build_eia_cme_wti_proxy(eia_spot, cme_points)
            proxies["EIA_WTI_FUT1"] = hybrid  # legacy internal proxy id
            sources["EIA_CME_WTI_PROXY"] = {
                "provider": "EIA spot + CME delayed settlements",
                "status": "ok",
                "latest": _latest(hybrid),
                "observations": len(hybrid),
                "role": "primary-source hybrid proxy for Brent spot",
                **hybrid_meta,
            }
        except Exception as exc:
            errors["EIA_CME_WTI_PROXY"] = str(exc)
            sources["EIA_CME_WTI_PROXY"] = {
                "provider": "EIA spot + CME delayed settlements",
                "status": "error",
            }

    return proxies, sources, errors


__all__ = [
    "CME_WTI_PRODUCT_ID",
    "CME_WTI_SETTLEMENT_URL",
    "EIA_WTI_SERIES",
    "build_eia_cme_wti_proxy",
    "fetch_primary_fast_proxies",
    "fetch_recent_cme_wti_settlements",
    "parse_cme_wti_settlement",
]
