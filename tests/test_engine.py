import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.engine import derived_metrics, evaluate


def points(old, new):
    return [{"date": "2026-05-01", "value": old}, {"date": "2026-08-20", "value": new}]


class EngineTests(unittest.TestCase):
    def test_h1_requires_triple_and_confirmation(self):
        data = {
            "DTWEXBGS": points(100, 94),
            "DFII10": points(2.0, 2.6),
            "T10YIE": points(2.2, 2.6),
            "SOFR": points(3.5, 4.0),
            "IORB": points(3.5, 3.7),
        }
        result = evaluate(data)
        self.assertEqual(result["regime"], "H1")
        self.assertEqual(result["triple_active"], 3)

    def test_h0_for_global_duration_without_us_excess(self):
        data = {"DGS10": points(4.0, 4.4)}
        for key in ("IRLTLT01JPM156N", "IRLTLT01DEM156N", "IRLTLT01GBM156N"):
            data[key] = points(2.0, 2.5)
        result = evaluate(data)
        self.assertEqual(result["regime"], "H0")

    def test_missing_data_is_indeterminate(self):
        self.assertEqual(evaluate({})["regime"], "INDETERMINADO")

    def test_vix_can_confirm_the_triple_signal(self):
        data = {
            "DTWEXBGS": points(100, 94),
            "DFII10": points(2.0, 2.6),
            "T10YIE": points(2.2, 2.6),
            "VIXCLS": points(18, 36),
        }
        result = evaluate(data)
        self.assertEqual(result["regime"], "H1")
        stress = next(signal for signal in result["signals"] if signal["key"] == "stress")
        self.assertTrue(stress["active"])

    def test_capex_metric_aggregates_at_least_three_companies(self):
        data = {
            "CAPEX_MSFT": points(40, 50),
            "CAPEX_GOOG": points(35, 45),
            "CAPEX_AMZN": points(48, 60),
        }
        metric = next(item for item in derived_metrics(data) if item["id"] == "AI_CAPEX_FY")
        self.assertEqual(metric["value"], 155)


if __name__ == "__main__":
    unittest.main()
