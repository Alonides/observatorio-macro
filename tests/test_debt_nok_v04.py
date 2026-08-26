import math
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.debt_nok_v04.backtest import run_continuous_backtest
from observatorio.debt_nok_v04.regime import evaluate_regimes
from observatorio.debt_nok_v04.residual import build_nok_residual
from observatorio.debt_nok_v04.scenarios import (
    dollar_shortage,
    false_usdnok_reversal,
    norwegian_reversal_confirmed,
    us_rejection,
    us_rejection_regime,
)


def residual_synthetic(days=1300, shock_start=None, shock_size=0.0):
    start = date(2000, 1, 3)
    eur_nok = 8.0
    eur_sek = 8.5
    brent = 50.0
    vix = 20.0
    output = {
        key: [] for key in (
            "DEXNOUS", "DEXUSEU", "DEXSDUS", "DCOILBRENTEU", "VIXCLS"
        )
    }
    current = start
    made = 0
    session = 0
    while made < days:
        if current.weekday() < 5:
            eursek_return = (
                0.0008 * math.sin(session / 13.0)
                + 0.0003 * math.cos(session / 31.0)
            )
            brent_return = 0.0020 * math.cos(session / 17.0)
            vix_return = 0.0025 * math.sin(session / 11.0)
            shock = (
                shock_size
                if shock_start is not None and shock_start <= session < shock_start + 20
                else 0.0
            )
            eurnok_return = (
                0.58 * eursek_return
                - 0.055 * brent_return
                + 0.006 * vix_return
                + shock
            )
            eur_sek *= math.exp(eursek_return)
            brent *= math.exp(brent_return)
            vix *= math.exp(vix_return)
            eur_nok *= math.exp(eurnok_return)
            day = current.isoformat()
            # USD/EUR remains one so the derived crosses are transparent.
            output["DEXUSEU"].append({"date": day, "value": 1.0})
            output["DEXNOUS"].append({"date": day, "value": eur_nok})
            output["DEXSDUS"].append({"date": day, "value": eur_sek})
            output["DCOILBRENTEU"].append({"date": day, "value": brent})
            output["VIXCLS"].append({"date": day, "value": vix})
            made += 1
            session += 1
        current += timedelta(days=1)
    return output


class DebtNokV04Tests(unittest.TestCase):
    def test_rejection_pulse_survives_correction(self):
        result = evaluate_regimes(us_rejection())
        self.assertEqual(result["model_version"], "0.4.1")
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

    def test_continuous_output_contains_urr_nrs_and_residual(self):
        result = run_continuous_backtest(us_rejection())
        self.assertEqual(result["model_version"], "0.4.1")
        self.assertIn("urr", result["blocks"])
        self.assertIn("nrs", result["blocks"])
        self.assertIn("nok_residual", result)
        self.assertIn("latest", result)
        self.assertIn("validated_episodes_ge_50", result["blocks"]["nks"])
        self.assertIn("persistent_validated_episodes_ge_50", result["blocks"]["nks"])
        self.assertGreaterEqual(result["blocks"]["urp"]["max_score"], 50.0)

    def test_nrs_reporting_uses_recovery_windows(self):
        result = run_continuous_backtest(norwegian_reversal_confirmed())
        self.assertIn("recovery_windows", result["blocks"]["nrs"])
        self.assertNotIn("event_windows", result["blocks"]["nrs"])
        self.assertGreater(result["blocks"]["nrs"]["confirmed_sessions"], 0)

    def test_explainable_nok_path_keeps_residual_below_stress_threshold(self):
        result = build_nok_residual(residual_synthetic())
        self.assertGreater(len(result["points"]), 200)
        tail = [abs(point["value"]) for point in result["points"][-100:]]
        self.assertLess(max(tail), 2.0)

    def test_idiosyncratic_nok_shock_activates_residual(self):
        result = build_nok_residual(
            residual_synthetic(shock_start=1100, shock_size=0.004)
        )
        self.assertGreater(max(point["value"] for point in result["points"]), 3.5)

    def test_residual_has_no_lookahead(self):
        base = residual_synthetic(days=1100)
        extended = residual_synthetic(days=1300, shock_start=1150, shock_size=0.01)
        first = build_nok_residual(base)["points"]
        second = build_nok_residual(extended)["points"]
        cutoff = first[-1]["date"]
        second_past = [point for point in second if point["date"] <= cutoff]
        self.assertEqual(first, second_past)


if __name__ == "__main__":
    unittest.main()
