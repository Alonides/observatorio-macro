"""Empirically corrected debt/NOK regime classifier v0.4.

This module is an isolated overlay on the frozen v0.3 implementation.  The
continuous 2006-present test showed that a high but *falling* VIX generated
false US-rejection pulses during recovery phases.  v0.4 therefore requires a
fresh risk-off onset: either the S&P 500 is down at least 3% over ten sessions,
or VIX is at least 25 and has risen at least five points or 20%.
"""

from __future__ import annotations

from datetime import date
from typing import Mapping, Sequence

from .. import regime as _base

MODEL_VERSION = "0.4.0"

# Make the correction explicit and visible in serialized parameters.
_base.MODEL_VERSION = MODEL_VERSION
_base.PARAMETERS["urp"]["vix_onset_points"] = 5.0
_base.PARAMETERS["urp"]["vix_onset_pct"] = 20.0


def _risk_block(md: _base.MarketData, asof: date) -> dict:
    spx_decline = None
    spx = md.view("SP500")
    if spx.dates:
        change = spx.pct_change(10, asof)
        spx_decline = None if change is None else -change

    vix_view = md.view("VIXCLS")
    vix = vix_view.value(asof)
    vix_change_10 = vix_view.change(10, asof)
    vix_change_10_pct = vix_view.pct_change(10, asof)

    spx_score = _base._score_up(spx_decline, _base.PARAMETERS["urp"]["spx_drop_pct"])
    vix_score = _base._score_up(vix, _base.PARAMETERS["urp"]["vix_level"])
    scores = [score for score in (spx_score, vix_score) if score is not None]
    score = max(scores) if scores else None

    spx_gate = spx_decline is not None and spx_decline >= 3.0
    vix_onset = bool(
        vix is not None
        and vix >= 25.0
        and (
            (vix_change_10 is not None and vix_change_10 >= 5.0)
            or (vix_change_10_pct is not None and vix_change_10_pct >= 20.0)
        )
    )

    return {
        "score": score,
        "gate": bool(spx_gate or vix_onset),
        "sp500_decline_10_pct": spx_decline,
        "vix": vix,
        "vix_change_10_points": vix_change_10,
        "vix_change_10_pct": vix_change_10_pct,
        "vix_onset": vix_onset,
        "method": (
            "Severity is max(S&P 500 decline, VIX level); the gate requires "
            "an equity fall or a high and rising VIX. A high but falling VIX "
            "does not open the gate."
        ),
    }


# _urp_at resolves _risk_block from the base module at call time, so replacing
# this single global preserves the audited v0.3 equations and changes only the
# empirically falsified risk-onset condition.
_base._risk_block = _risk_block

MarketData = _base.MarketData
SeriesView = _base.SeriesView
PARAMETERS = _base.PARAMETERS


def evaluate_regimes(
    series: Mapping[str, Sequence[Mapping[str, object]]],
    asof: str | date | None = None,
) -> dict:
    result = _base.evaluate_regimes(series, asof=asof)
    result["model_version"] = MODEL_VERSION
    result["parameters"] = PARAMETERS
    result["method_note_v04"] = (
        "URP requires a fresh risk-off onset. Elevated but declining VIX is "
        "treated as aftermath/recovery, not a new rejection pulse."
    )
    return result


__all__ = [
    "MODEL_VERSION",
    "PARAMETERS",
    "MarketData",
    "SeriesView",
    "evaluate_regimes",
]
