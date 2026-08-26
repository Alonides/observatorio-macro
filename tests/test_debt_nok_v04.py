import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.debt_nok_v04.backtest import run_continuous_backtest
from observatorio.debt_nok_v04.regime import evaluate_regimes
from observatorio.debt_nok_v04.scenarios import (
    dollar_shortage,
    false_usdnok_reversal,
    norwegian_reversal_confirmed,
    us_rejection,
    us_rejection_regime,
)


class DebtNokV04Tests(unittest.TestCase):
    def test_rejection_pulse_survives_correction(self):
        result = evaluate_regimes(us_rejection())
        self.assertEqual(result["model_version"], "0.4.0")
        self.assertGreaterEqual(result["urp"]["score"], 50.0)
        self.assertTrue(result["urp"]["values"]["vix_onset"])

    def test_high_but_falling_vix_does_not_open_gate(self):
        data = us_rejection()
        days = [point["date"] for point in data["VIXCLS"]]
        values = [45.0] * 89 + [45.0 - 1.5 * step for step in range(11)]
        data["VIXCLS"] = [
            {"date": day, "value": value}
            for day, value in zip(days, values)
        ]
        result = evaluate_regimes(data)
        self.assertEqual(result["urp"]["score"], 0.0)
        self.assertFalse(result["urp"]["values"]["vix_onset"])

    def test_persistent_synthetic_case_reaches_regime(self):
        result = evaluate_regimes(us_rejection_regime())
        self.assertEqual(result["urr"]["state"], "rejection_regime")

    def test_dollar_shortage_remains_separate(self):
        result = evaluate_regimes(dollar_shortage())
        self.assertEqual(result["urp"]["score"], 0.0)
        self.assertGreaterEqual(result["dss"]["score"], 50.0)

    def test_usdnok_only_recovery_is_not_norwegian_reversal(self):
        result = evaluate_regimes(false_usdnok_reversal())
        self.assertEqual(result["nrs"]["state"], "inactive")

    def test_residual_can_confirm_norwegian_reversal(self):
        result = evaluate_regimes(norwegian_reversal_confirmed())
        self.assertEqual(result["nrs"]["state"], "confirmed")

    def test_continuous_output_contains_urr(self):
        result = run_continuous_backtest(us_rejection())
        self.assertEqual(result["model_version"], "0.4.0")
        self.assertIn("urr", result["blocks"])
        self.assertGreaterEqual(result["blocks"]["urp"]["max_score"], 50.0)


if __name__ == "__main__":
    unittest.main()
