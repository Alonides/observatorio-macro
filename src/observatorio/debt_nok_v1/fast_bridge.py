"""Official-source fast bridge for Debt/NOK v1.0.3.

The validated v0.4.1 core remains untouched. This module can extend a handful
of slow official series for a few business days using faster *proxy* series:

* ECB reference rates extend the Federal Reserve H.10 EUR, NOK and SEK crosses;
* a six-currency ECB dollar basket extends the Fed broad-dollar index;
* EIA WTI futures contract 1 extends EIA Brent spot.

Every extension is return-spliced to the last official level, validated on an
overlap window and labelled provisional. It never overwrites an official
observation and expires when the official anchor is too old.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from math import exp, isfinite, log, sqrt
from statistics import mean
from typing import Callable, Mapping, Sequence
from xml.etree import ElementTree

from ..official import SourceError, _eia, _read


FAST_BRIDGE_VERSION = "1.0.3"
ECB_REFERENCE_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
EIA_WTI_ROUTE = "petroleum/pri/fut"
EIA_WTI_SERIES = "RCLC1"

LEVEL_RANK = {"normal": 0, "watch": 1, "alert": 2, "critical": 3}
LEVEL_LABEL = {
    "normal": "Normal",
    "watch": "Vigilancia provisional",
    "alert": "Alerta provisional",
    "critical": "Alerta provisional máxima",
}


@dataclass(frozen=True)
class BridgeRule:
    target: str
    proxy: str
    label: str
    max_business_days: int
    minimum_overlap_returns: int
    minimum_correlation: float
    maximum_mae_pct: float
    maximum_anchor_gap_days: int
    maximum_bridge_move_pct: float


RULES: tuple[BridgeRule, ...] = (
    BridgeRule(
        "DEXUSEU", "ECB_DEXUSEU", "ECB USD por EUR",
        5, 10, 0.995, 0.15, 1, 3.0,
    ),
    BridgeRule(
        "DEXNOUS", "ECB_DEXNOUS", "ECB NOK por USD",
        5, 10, 0.995, 0.15, 1, 4.0,
    ),
    BridgeRule(
        "DEXSDUS", "ECB_DEXSDUS", "ECB SEK por USD",
        5, 10, 0.995, 0.15, 1, 4.0,
    ),
    BridgeRule(
        "DTWEXBGS", "ECB_DOLLAR_PROXY", "Cesta dólar ECB de seis divisas",
        4, 20, 0.60, 0.80, 1, 4.0,
    ),
    BridgeRule(
        "DCOILBRENTEU", "EIA_WTI_FUT1", "EIA WTI futuros, contrato 1",
        7, 20, 0.60, 2.50, 2, 20.0,
    ),
)


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


def _business_day_lag(start: date | None, end: date | None) -> int | None:
    if start is None or end is None:
        return None
    if start >= end:
        return 0
    current = start + timedelta(days=1)
    lag = 0
    while current <= end:
        if current.weekday() < 5:
            lag += 1
        current += timedelta(days=1)
    return lag


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
        (lvalue - left_mean) * (rvalue - right_mean)
        for lvalue, rvalue in zip(left, right)
    )
    return covariance / sqrt(left_var * right_var)


def tracking_statistics(
    official_points: Sequence[Mapping[str, object]],
    proxy_points: Sequence[Mapping[str, object]],
    window: int = 60,
) -> dict:
    official = _point_map(official_points)
    proxy = _point_map(proxy_points)
    common = sorted(official.keys() & proxy.keys())[-(window + 1):]
    official_returns: list[float] = []
    proxy_returns: list[float] = []
    for previous, current in zip(common, common[1:]):
        if (current - previous).days > 7:
            continue
        try:
            official_returns.append(log(official[current] / official[previous]))
            proxy_returns.append(log(proxy[current] / proxy[previous]))
        except (ValueError, ZeroDivisionError):
            continue
    correlation = _correlation(official_returns, proxy_returns)
    mae_pct = (
        mean(abs(left - right) for left, right in zip(official_returns, proxy_returns)) * 100.0
        if official_returns else None
    )
    sign_agreement = (
        mean(1.0 if left * right >= 0.0 else 0.0 for left, right in zip(official_returns, proxy_returns))
        if official_returns else None
    )
    return {
        "overlap_returns": len(official_returns),
        "correlation": None if correlation is None else round(correlation, 4),
        "mae_pct_points": None if mae_pct is None else round(mae_pct, 4),
        "sign_agreement": None if sign_agreement is None else round(sign_agreement, 4),
        "overlap_start": common[0].isoformat() if common else None,
        "overlap_end": common[-1].isoformat() if common else None,
    }


def parse_ecb_reference_xml(text: str) -> dict[str, list[dict]]:
    """Parse ECB EUR-base rates and derive the three FX crosses plus a DXY proxy."""
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        raise SourceError(f"ECB reference rates: XML inválido: {exc}") from exc

    required = {"USD", "JPY", "GBP", "CAD", "SEK", "CHF", "NOK"}
    output = {
        "ECB_DEXUSEU": [],
        "ECB_DEXNOUS": [],
        "ECB_DEXSDUS": [],
        "ECB_DOLLAR_PROXY": [],
    }
    for cube in root.iter():
        raw_day = cube.attrib.get("time")
        if not raw_day:
            continue
        try:
            day = date.fromisoformat(raw_day).isoformat()
        except ValueError:
            continue
        rates: dict[str, float] = {}
        for child in cube:
            currency = child.attrib.get("currency")
            raw_rate = child.attrib.get("rate")
            if not currency or raw_rate is None:
                continue
            try:
                value = float(raw_rate)
            except ValueError:
                continue
            if value > 0.0 and isfinite(value):
                rates[currency] = value
        if not required.issubset(rates):
            continue

        eurusd = rates["USD"]
        usdjpy = rates["JPY"] / eurusd
        gbpusd = eurusd / rates["GBP"]
        usdcad = rates["CAD"] / eurusd
        usdsek = rates["SEK"] / eurusd
        usdchf = rates["CHF"] / eurusd
        nokusd = rates["NOK"] / eurusd

        # Relative six-currency dollar basket. The absolute normalization is
        # irrelevant because the bridge uses only returns and re-anchors to the
        # official broad-dollar level.
        dollar_proxy = exp(
            -0.576 * log(eurusd)
            + 0.136 * log(usdjpy)
            - 0.119 * log(gbpusd)
            + 0.091 * log(usdcad)
            + 0.042 * log(usdsek)
            + 0.036 * log(usdchf)
        )
        output["ECB_DEXUSEU"].append({"date": day, "value": eurusd})
        output["ECB_DEXNOUS"].append({"date": day, "value": nokusd})
        output["ECB_DEXSDUS"].append({"date": day, "value": usdsek})
        output["ECB_DOLLAR_PROXY"].append({"date": day, "value": dollar_proxy})

    for key in output:
        output[key] = _points(_point_map(output[key]))
    if not output["ECB_DEXUSEU"]:
        raise SourceError("ECB reference rates: no se obtuvieron observaciones completas")
    return output


def _latest(points: Sequence[Mapping[str, object]]) -> str | None:
    values = _point_map(points)
    return max(values).isoformat() if values else None


def fetch_fast_proxies(
    read_bytes: Callable[..., bytes] = _read,
    eia_fetcher: Callable[[str, str], list[dict]] = _eia,
) -> tuple[dict[str, list[dict]], dict, dict[str, str]]:
    """Fetch the two official source packages used by the provisional bridge."""
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

    try:
        wti = eia_fetcher(EIA_WTI_ROUTE, EIA_WTI_SERIES)
        if not wti:
            raise SourceError("EIA WTI futures returned no observations")
        proxies["EIA_WTI_FUT1"] = wti
        sources["EIA_WTI_FUTURES"] = {
            "provider": "U.S. Energy Information Administration",
            "url": "https://api.eia.gov/v2/petroleum/pri/fut/",
            "series": EIA_WTI_SERIES,
            "status": "ok",
            "latest": _latest(wti),
            "observations": len(wti),
            "role": "official futures proxy for Brent spot",
        }
    except Exception as exc:
        errors["EIA_WTI_FUTURES"] = str(exc)
        sources["EIA_WTI_FUTURES"] = {
            "provider": "U.S. Energy Information Administration",
            "url": "https://api.eia.gov/v2/petroleum/pri/fut/",
            "series": EIA_WTI_SERIES,
            "status": "error",
        }

    return proxies, sources, errors


def _bridge_one(
    official_points: Sequence[Mapping[str, object]],
    proxy_points: Sequence[Mapping[str, object]],
    rule: BridgeRule,
) -> tuple[list[dict], dict]:
    official = _point_map(official_points)
    proxy = _point_map(proxy_points)
    metadata = {
        **asdict(rule),
        "status": "unavailable",
        "provisional": True,
        "official_last": max(official).isoformat() if official else None,
        "proxy_last": max(proxy).isoformat() if proxy else None,
        "bridge_start": None,
        "bridge_end": None,
        "bridge_observations": 0,
        "anchor_date": None,
        "validation": tracking_statistics(official_points, proxy_points),
    }
    if not official or not proxy:
        metadata["reason"] = "official_or_proxy_missing"
        return _points(official), metadata

    official_last = max(official)
    proxy_last = max(proxy)
    if proxy_last <= official_last:
        metadata["status"] = "not_needed"
        metadata["reason"] = "official_not_slower"
        return _points(official), metadata

    total_gap = _business_day_lag(official_last, proxy_last)
    if total_gap is None or total_gap > rule.max_business_days:
        metadata["status"] = "expired"
        metadata["reason"] = "official_anchor_too_old"
        metadata["business_day_gap"] = total_gap
        return _points(official), metadata

    validation = metadata["validation"]
    overlap = int(validation.get("overlap_returns") or 0)
    correlation = validation.get("correlation")
    mae = validation.get("mae_pct_points")
    if overlap < rule.minimum_overlap_returns:
        metadata["status"] = "rejected"
        metadata["reason"] = "insufficient_overlap"
        return _points(official), metadata
    if correlation is None or correlation < rule.minimum_correlation:
        metadata["status"] = "rejected"
        metadata["reason"] = "tracking_correlation_below_threshold"
        return _points(official), metadata
    if mae is None or mae > rule.maximum_mae_pct:
        metadata["status"] = "rejected"
        metadata["reason"] = "tracking_error_above_threshold"
        return _points(official), metadata

    anchor_candidates = [day for day in proxy if day <= official_last]
    if not anchor_candidates:
        metadata["status"] = "rejected"
        metadata["reason"] = "no_proxy_anchor"
        return _points(official), metadata
    anchor = max(anchor_candidates)
    anchor_gap = _business_day_lag(anchor, official_last)
    if anchor_gap is None or anchor_gap > rule.maximum_anchor_gap_days:
        metadata["status"] = "rejected"
        metadata["reason"] = "proxy_anchor_too_distant"
        metadata["anchor_gap"] = anchor_gap
        return _points(official), metadata

    anchor_value = proxy[anchor]
    official_level = official[official_last]
    future = [day for day in sorted(proxy) if day > official_last]
    if not future:
        metadata["status"] = "not_needed"
        metadata["reason"] = "no_future_proxy_points"
        return _points(official), metadata

    bridged: dict[date, float] = dict(official)
    candidate_values: list[tuple[date, float]] = []
    for day in future:
        value = official_level * proxy[day] / anchor_value
        if isfinite(value) and value > 0.0:
            candidate_values.append((day, value))
    if not candidate_values:
        metadata["status"] = "rejected"
        metadata["reason"] = "no_valid_bridge_values"
        return _points(official), metadata

    maximum_move = max(abs(value / official_level - 1.0) * 100.0 for _, value in candidate_values)
    if maximum_move > rule.maximum_bridge_move_pct:
        metadata["status"] = "rejected"
        metadata["reason"] = "bridge_move_above_guardrail"
        metadata["maximum_bridge_move_pct_observed"] = round(maximum_move, 4)
        return _points(official), metadata

    for day, value in candidate_values:
        bridged[day] = value
    metadata.update({
        "status": "active",
        "reason": "proxy_return_splice",
        "business_day_gap": total_gap,
        "anchor_date": anchor.isoformat(),
        "bridge_start": candidate_values[0][0].isoformat(),
        "bridge_end": candidate_values[-1][0].isoformat(),
        "bridge_observations": len(candidate_values),
        "maximum_bridge_move_pct_observed": round(maximum_move, 4),
    })
    return _points(bridged), metadata


def build_fast_series(
    series: Mapping[str, Sequence[Mapping[str, object]]],
    proxies: Mapping[str, Sequence[Mapping[str, object]]] | None = None,
    sources: Mapping[str, object] | None = None,
    errors: Mapping[str, str] | None = None,
) -> tuple[dict[str, list[dict]], dict]:
    """Return a copy extended only beyond each target's last official date."""
    output = {key: list(value) for key, value in series.items()}
    proxies = proxies or {}
    targets: dict[str, dict] = {}
    for rule in RULES:
        combined, metadata = _bridge_one(
            output.get(rule.target, ()),
            proxies.get(rule.proxy, ()),
            rule,
        )
        output[rule.target] = combined
        targets[rule.target] = metadata

    active = sorted(key for key, item in targets.items() if item.get("status") == "active")
    rejected = sorted(key for key, item in targets.items() if item.get("status") in {"rejected", "expired"})
    metadata = {
        "version": FAST_BRIDGE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "available": bool(active),
        "status": "active" if active else "degraded" if rejected or errors else "not_needed",
        "active_targets": active,
        "rejected_or_expired_targets": rejected,
        "targets": targets,
        "sources": dict(sources or {}),
        "errors": dict(errors or {}),
        "method": (
            "Returns from faster official proxy series are spliced to the last official "
            "level. Official observations are never overwritten; every splice is "
            "short-lived, overlap-validated and provisional."
        ),
    }
    return output, metadata


def build_fast_lane_payload(official_result: dict, provisional_result: dict, bridge: dict) -> dict:
    official_operational = official_result.get("operational", {})
    provisional_operational = provisional_result.get("operational", {})
    official_level = str(official_operational.get("level") or "normal")
    raw_level = str(provisional_operational.get("level") or "normal")
    raw_rank = LEVEL_RANK.get(raw_level, 0)
    official_rank = LEVEL_RANK.get(official_level, 0)
    display_level = "alert" if raw_rank >= LEVEL_RANK["alert"] else raw_level
    divergence = raw_rank > official_rank
    review_required = divergence and raw_rank >= LEVEL_RANK["alert"]

    comparisons: dict[str, dict] = {}
    official_blocks = official_operational.get("blocks", {})
    provisional_blocks = provisional_operational.get("blocks", {})
    for key in ("URP", "URR", "DSS", "NKS", "NRS"):
        official_block = official_blocks.get(key, {})
        provisional_block = provisional_blocks.get(key, {})
        try:
            delta = float(provisional_block.get("score") or 0.0) - float(official_block.get("score") or 0.0)
        except (TypeError, ValueError):
            delta = 0.0
        comparisons[key] = {
            "official_score": official_block.get("score"),
            "provisional_score": provisional_block.get("score"),
            "delta": round(delta, 2),
            "official_state": official_block.get("state"),
            "provisional_state": provisional_block.get("state"),
            "official_asof": official_block.get("asof"),
            "provisional_asof": provisional_block.get("asof"),
        }

    if not bridge.get("available"):
        status = "unavailable"
        message = "No hay una extensión provisional validada más reciente que la lectura oficial."
    elif divergence:
        status = "divergent"
        message = (
            "La vía rápida provisional es más severa que la lectura oficial y requiere "
            "confirmación con la siguiente publicación primaria."
        )
    else:
        status = "aligned"
        message = "La vía rápida provisional no eleva el nivel de la lectura oficial."

    active_signature = ",".join(
        f"{target}:{bridge.get('targets', {}).get(target, {}).get('bridge_end')}"
        for target in bridge.get("active_targets", [])
    )
    states = ",".join(
        str(provisional_blocks.get(key, {}).get("state") or "missing")
        for key in ("URP", "URR", "DSS", "NKS", "NRS")
    )
    return {
        "version": FAST_BRIDGE_VERSION,
        "provisional": True,
        "available": bool(bridge.get("available")),
        "status": status,
        "official_level": official_level,
        "raw_provisional_level": raw_level,
        "level": display_level,
        "label": LEVEL_LABEL.get(display_level, "Provisional"),
        "divergence": divergence,
        "review_required": review_required,
        "message": message,
        "asof": provisional_result.get("asof"),
        "block_asof": provisional_result.get("block_asof", {}),
        "freshness": provisional_result.get("freshness", {}),
        "comparisons": comparisons,
        "operational": provisional_operational,
        "bridge": bridge,
        "fingerprint": f"{official_level}|{raw_level}|{states}|{active_signature}",
        "disclaimer": (
            "La vía rápida usa proxies oficiales correlacionados y no confirma por sí "
            "sola un cambio de régimen. La lectura oficial conserva prioridad."
        ),
    }


__all__ = [
    "ECB_REFERENCE_URL",
    "FAST_BRIDGE_VERSION",
    "RULES",
    "build_fast_lane_payload",
    "build_fast_series",
    "fetch_fast_proxies",
    "parse_ecb_reference_xml",
    "tracking_statistics",
]
