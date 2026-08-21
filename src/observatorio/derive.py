"""Series derivadas con formulas explicitas y alineacion temporal acotada."""

from __future__ import annotations

from datetime import date


def _asof_binary(
    left: list[dict],
    right: list[dict],
    operation,
    max_gap_days: int = 7,
) -> list[dict]:
    """Aplica una formula usando el ultimo dato derecho conocido en esa fecha."""
    left_clean = sorted(
        (point for point in left if point.get("date") and point.get("value") is not None),
        key=lambda point: point["date"],
    )
    right_clean = sorted(
        (point for point in right if point.get("date") and point.get("value") is not None),
        key=lambda point: point["date"],
    )
    output = []
    right_index = 0
    candidate = None
    for left_point in left_clean:
        left_day = date.fromisoformat(left_point["date"])
        while right_index < len(right_clean) and right_clean[right_index]["date"] <= left_point["date"]:
            candidate = right_clean[right_index]
            right_index += 1
        if candidate is None:
            continue
        gap = (left_day - date.fromisoformat(candidate["date"])).days
        if gap < 0 or gap > max_gap_days:
            continue
        try:
            value = operation(float(left_point["value"]), float(candidate["value"]))
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        output.append({"date": left_point["date"], "value": value})
    return output


def derive_series(series: dict[str, list[dict]]) -> dict[str, list[dict]]:
    gold = series.get("GOLDAMGBD228NLBM", [])
    output = {
        "SP500_XAU": _asof_binary(series.get("SP500", []), gold, lambda equity, gold_usd: equity / gold_usd),
        "BTC_XAU": _asof_binary(series.get("CBBTCUSD", []), gold, lambda bitcoin, gold_usd: bitcoin / gold_usd),
        "XAU_NOK": _asof_binary(gold, series.get("DEXNOUS", []), lambda gold_usd, nok_usd: gold_usd * nok_usd),
        "XAU_EUR": _asof_binary(gold, series.get("DEXUSEU", []), lambda gold_usd, usd_eur: gold_usd / usd_eur),
        "XAU_JPY": _asof_binary(gold, series.get("DEXJPUS", []), lambda gold_usd, jpy_usd: gold_usd * jpy_usd),
        "XAU_CNY": _asof_binary(gold, series.get("DEXCHUS", []), lambda gold_usd, cny_usd: gold_usd * cny_usd),
        "US_PUBLIC_DEBT_XAU": _asof_binary(
            series.get("US_DEBT_HELD_PUBLIC", []), gold, lambda debt_musd, gold_usd: debt_musd / gold_usd
        ),
        "US_GROSS_DEBT_XAU": _asof_binary(
            series.get("GFDEBTN", []), gold, lambda debt_musd, gold_usd: debt_musd / gold_usd
        ),
    }
    return output
