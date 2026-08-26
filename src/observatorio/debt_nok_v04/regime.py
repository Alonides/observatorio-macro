"""Empirically corrected debt/NOK regime classifier v0.4.1.

v0.4 corrected a false-positive mechanism in URP: an elevated but falling VIX
was being mistaken for a fresh risk-off event. v0.4.1 adds the causal,
walk-forward NOK residual used by NKS and NRS while preserving the audited v0.3
score equations.
"""

from __future__ import annotations

from datetime import date
from typing import Mapping, Sequence

from .. import regime as _base
from .residual import RESIDUAL_PARAMETERS, attach_nok_residual

MODEL_VERSION = "0.4.1"

# Make the corrections explicit and visible in serialized parameters.
_base.MODEL_VERSION = MODEL_VERSION
_base.PARAMETERS["urp"]["vix_onset_points"] = 5.0
_base.PARAMETERS["urp"]["vix_onset_pct"] = 20.0
_base.PARAMETERS["nok_residual"] = RESIDUAL_PARAMETERS


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
# this global changes only the empirically falsified risk-onset condition.
_base._risk_block = _risk_block

MarketData = _base.MarketData
SeriesView = _base.SeriesView
PARAMETERS = _base.PARAMETERS


def _clarify_nrs_semantics(result: dict) -> None:
    """Separate descriptive gate completion from an operational alert score.

    The v0.3/v0.4 NRS `score` is the percentage of observable gates currently
    satisfied. That is useful diagnostically, but it is not an alert severity:
    an inactive reversal can still satisfy several benign recovery gates.
    Preserve the diagnostic value as `gate_score` and expose an explicit
    `operational_score` that is non-zero only when NRS is confirmed.
    """
    nrs = result.get("nrs")
    if not isinstance(nrs, dict):
        return
    gate_score = nrs.get("score")
    nrs["gate_score"] = gate_score
    nrs["operational_active"] = nrs.get("state") == "confirmed"
    nrs["operational_score"] = gate_score if nrs["operational_active"] else 0.0
    nrs["score_semantics"] = (
        "gate_score is descriptive gate completion; operational_score is zero "
        "unless the full NRS confirmation state is reached."
    )


def evaluate_regimes(
    series: Mapping[str, Sequence[Mapping[str, object]]],
    asof: str | date | None = None,
) -> dict:
    enriched, residual_diagnostics = attach_nok_residual(series)
    result = _base.evaluate_regimes(enriched, asof=asof)
    result["model_version"] = MODEL_VERSION
    result["parameters"] = PARAMETERS
    result["nok_residual"] = residual_diagnostics
    _clarify_nrs_semantics(result)
    result["method_note_v041"] = (
        "URP requires a fresh risk-off onset. NKS and NRS use a walk-forward "
        "Huber residual of EUR/NOK against EUR/SEK, Brent and VIX. Every score "
        "at t is fitted and standardised only with information available before t. "
        "NRS gate completion is reported separately from its operational alert."
    )
    return result


__all__ = [
    "MODEL_VERSION",
    "PARAMETERS",
    "MarketData",
    "SeriesView",
    "evaluate_regimes",
]
