import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.regime import evaluate_regimes
from observatorio.scenarios import (
    dollar_shortage,
    duration_shock,
    false_usdnok_reversal,
    nok_stress,
    norwegian_reversal_candidate,
    norwegian_reversal_confirmed,
    us_rejection,
    us_rejection_regime,
)


class RegimeModelTests(unittest.TestCase):
    def test_duration_shock_is_not_us_rejection(self):
        result = evaluate_regimes(duration_shock())
        self.assertEqual(result["urp"]["score"], 0.0)
        self.assertTrue(result["dss"]["gate"])

    def test_us_rejection_activates_urp_and_relative_confirmation(self):
        result = evaluate_regimes(us_rejection())
        self.assertGreaterEqual(result["urp"]["score"], 50.0)
        self.assertTrue(result["urp"]["relative_confirmed"])
        self.assertIn(result["urp"]["state"], {"confirmed_pulse", "unconfirmed_pulse"})

    def test_persistent_us_rejection_reaches_regime(self):
        result = evaluate_regimes(us_rejection_regime())
        self.assertEqual(result["urr"]["state"], "rejection_regime")
        self.assertTrue(result["urr"]["rejection_regime"])

    def test_dollar_shortage_is_separate_from_rejection(self):
        result = evaluate_regimes(dollar_shortage())
        self.assertEqual(result["urp"]["score"], 0.0)
        self.assertGreaterEqual(result["dss"]["score"], 50.0)
        self.assertEqual(result["dss"]["state"], "traditional_safe_haven")

    def test_nok_stress_is_detected(self):
        result = evaluate_regimes(nok_stress())
        self.assertGreaterEqual(result["nks"]["score"], 65.0)
        self.assertEqual(result["nks"]["state"], "severe")

    def test_usdnok_only_recovery_does_not_trigger_nrs(self):
        result = evaluate_regimes(false_usdnok_reversal())
        self.assertEqual(result["nrs"]["state"], "inactive")
        self.assertFalse(result["nrs"]["gates"].get("eurnok_recovery", False))

    def test_true_observable_reversal_is_candidate_without_residual(self):
        result = evaluate_regimes(norwegian_reversal_candidate())
        self.assertEqual(result["nrs"]["state"], "candidate_unconfirmed_residual_missing")
        self.assertIsNone(result["nrs"]["gates"]["negative_nok_residual"])

    def test_reversal_is_confirmed_when_residual_agrees(self):
        result = evaluate_regimes(norwegian_reversal_confirmed())
        self.assertEqual(result["nrs"]["state"], "confirmed")
        self.assertTrue(result["nrs"]["gates"]["negative_nok_residual"])

    def test_missing_data_is_reported_not_imputed(self):
        result = evaluate_regimes({})
        self.assertEqual(result["status"], "insufficient_data")
        self.assertIsNone(result["urp"])


if __name__ == "__main__":
    unittest.main()
