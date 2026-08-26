"""Synthetic falsification scenarios evaluated through the v0.4 overlay."""

# Importing the overlay patches the base classifier before the scenario module
# binds its evaluate_regimes reference.
from . import regime as _v4  # noqa: F401
from ..scenarios import (
    dollar_shortage,
    duration_shock,
    false_usdnok_reversal,
    nok_stress,
    norwegian_reversal_candidate,
    norwegian_reversal_confirmed,
    synthetic_results,
    us_rejection,
    us_rejection_regime,
)

__all__ = [
    "duration_shock",
    "us_rejection",
    "us_rejection_regime",
    "dollar_shortage",
    "nok_stress",
    "false_usdnok_reversal",
    "norwegian_reversal_candidate",
    "norwegian_reversal_confirmed",
    "synthetic_results",
]
