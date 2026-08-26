"""Frozen v1.0.3 calibration for provisional bridge admissibility.

ECB and Federal Reserve H.10 publish the same currency crosses at different
fixing times. Their daily-return correlations are therefore materially lower
than one even though the level identity is exact. The thresholds below were
fixed after the initial live calibration run on 26 August 2026. That run is a
calibration observation, not an out-of-sample validation; later scheduled runs
are the prospective test.

This configuration changes only whether a *provisional* bridge may be shown. It
does not change official series, model equations, scores, alert thresholds or
historical backtests.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from .fast_bridge import BridgeRule


FX_CALIBRATION = {
    # Initial live calibration: corr 0.6020, MAE 0.2291 percentage points.
    "DEXUSEU": {"minimum_correlation": 0.58, "maximum_mae_pct": 0.35},
    # Initial live calibration: corr 0.7084, MAE 0.2984 percentage points.
    "DEXNOUS": {"minimum_correlation": 0.65, "maximum_mae_pct": 0.42},
    # Initial live calibration: corr 0.6453, MAE 0.3999 percentage points.
    "DEXSDUS": {"minimum_correlation": 0.60, "maximum_mae_pct": 0.52},
}


def configure_v103_rules(rules: Sequence[BridgeRule]) -> tuple[BridgeRule, ...]:
    """Return immutable rules with the declared direct-FX calibration applied."""
    output: list[BridgeRule] = []
    for rule in rules:
        calibration = FX_CALIBRATION.get(rule.target)
        if calibration:
            output.append(replace(rule, **calibration))
        else:
            output.append(rule)
    return tuple(output)


__all__ = ["FX_CALIBRATION", "configure_v103_rules"]
