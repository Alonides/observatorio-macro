import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.debt_nok_v04.scenarios import norwegian_reversal_confirmed
from observatorio.debt_nok_v1.monitor import MODEL_VERSION, evaluate_operational
from observatorio.debt_nok_v1.report import build_report


def staggered_data():
    data = norwegian_reversal_confirmed()
    data["DTWEXBGS"] = data["DTWEXBGS"][:-1]
    for key in ("DEXNOUS", "DEXUSEU", "DEXSDUS"):
        data[key] = data[key][:-2]
    data["DCOILBRENTEU"] = data["DCOILBRENTEU"][:-3]
    data["NOK_RESIDUAL_Z20"] = data["NOK_RESIDUAL_Z20"][:-4]
    return data


class DebtNokFreshnessTests(unittest.TestCase):
    def test_each_block_uses_its_latest_complete_date(self):
        result = evaluate_operational(staggered_data())
        self.assertEqual(result["model_version"], MODEL_VERSION)
        self.assertEqual(result["block_asof"]["URP"], "2026-04-09")
        self.assertEqual(result["block_asof"]["URR"], "2026-04-09")
        self.assertEqual(result["block_asof"]["DSS"], "2026-04-09")
        self.assertEqual(result["block_asof"]["NKS"], "2026-04-06")
        self.assertEqual(result["block_asof"]["NRS"], "2026-04-06")
        self.assertEqual(result["asof"], "2026-04-09")
        self.assertEqual(result["freshness"]["latest_input_date"], "2026-04-10")
        self.assertEqual(result["freshness"]["blocks"]["NKS"]["business_day_lag"], 4)
        self.assertEqual(result["freshness"]["quality"], "stale")
        self.assertEqual(result["operational"]["blocks"]["NKS"]["asof"], "2026-04-06")

    def test_explicit_asof_preserves_synchronous_historical_evaluation(self):
        result = evaluate_operational(staggered_data(), asof="2026-03-20")
        self.assertTrue(all(day == "2026-03-20" for day in result["block_asof"].values()))

    def test_report_date_is_generation_date_in_oslo_not_market_date(self):
        report = build_report(
            staggered_data(),
            mode="weekly",
            generated_at="2026-08-26T22:30:00+00:00",
        )
        self.assertEqual(report["report_date"], "2026-08-27")
        self.assertEqual(report["asof"], "2026-04-09")
        self.assertIn("# Informe Debt/NOK · 2026-08-27", report["markdown"])
        self.assertIn("Frescura oficial de los bloques", report["markdown"])
        self.assertIn("Datos a", report["markdown"])
        self.assertTrue(report["notification_title"].endswith("2026-08-27"))

    def test_previous_comparison_dates_are_block_specific(self):
        report = build_report(staggered_data(), generated_at="2026-08-26T10:00:00+00:00")
        previous = report["previous_block_asof"]
        self.assertEqual(previous["URP"], "2026-04-04")
        self.assertEqual(previous["NKS"], "2026-04-01")
        self.assertNotEqual(previous["URP"], previous["NKS"])


if __name__ == "__main__":
    unittest.main()
