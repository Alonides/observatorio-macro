import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.engine import derived_metrics, evaluate


def points(old, new):
    return [{"date": "2026-05-01", "value": old}, {"date": "2026-08-20", "value": new}]


def peer_data(us_change, peer_changes):
    data = {"DGS10": points(4.0, 4.0 + us_change)}
    for key, change in zip(
        ("IRLTLT01JPM156N", "IRLTLT01DEM156N", "IRLTLT01GBM156N"),
        peer_changes,
    ):
        data[key] = points(2.0, 2.0 + change)
    return data


class EngineTests(unittest.TestCase):
    def test_h2_is_global_duration_not_h0(self):
        data = peer_data(0.4, (0.5, 0.5, 0.5))
        result = evaluate(data)
        self.assertEqual(result["regime"], "H2")
        self.assertEqual(result["diagnostics"]["markets_rising"], 4)

    def test_h0_requires_positive_us_specific_evidence(self):
        data = peer_data(0.8, (-0.1, -0.1, -0.1))
        result = evaluate(data)
        self.assertEqual(result["regime"], "H0")
        self.assertEqual(result["evidence_level"], "compatible")

    def test_absence_of_h1_does_not_prove_h0(self):
        self.assertEqual(evaluate({"DGS10": points(4.0, 4.4)})["regime"], "INDETERMINATE")

    def test_h1_requires_triple_specificity_and_confirmation(self):
        data = peer_data(0.9, (-0.1, -0.1, -0.1))
        data.update({
            "DTWEXBGS": points(100, 96),
            "DFII10": points(2.0, 2.4),
            "T10YIE": points(2.2, 2.5),
            "SOFR": points(3.5, 4.0),
            "IORB": points(3.5, 3.7),
        })
        result = evaluate(data)
        self.assertEqual(result["regime"], "H1")
        self.assertEqual(result["triple_active"], 3)
        self.assertEqual(result["evidence_level"], "candidate")

    def test_mixed_is_reachable(self):
        data = peer_data(1.2, (0.45, 0.45, 0.45))
        data.update({
            "DTWEXBGS": points(100, 96),
            "DFII10": points(2.0, 2.4),
            "T10YIE": points(2.2, 2.5),
            "VIXCLS": points(18, 40),
        })
        self.assertEqual(evaluate(data)["regime"], "MIXED")

    def test_reflation_signature_is_context_not_h1_verdict(self):
        data = peer_data(0.4, (0.5, 0.5, 0.5))
        data.update({
            "DTWEXBGS": points(100, 96),
            "DFII10": points(2.0, 2.4),
            "T10YIE": points(2.2, 2.5),
            "SP500": points(1000, 1120),
            "BAMLC0A0CM": points(3.0, 2.0),
        })
        result = evaluate(data)
        self.assertNotEqual(result["regime"], "H1")
        self.assertEqual(result["risk_context"]["classification"], "REFLATION_COMPATIBLE")
        self.assertEqual(result["context"], "TRIPLE_ALERT")

    def test_vix_without_us_specificity_cannot_create_h1(self):
        data = peer_data(0.4, (0.5, 0.5, 0.5))
        data.update({
            "DTWEXBGS": points(100, 96),
            "DFII10": points(2.0, 2.4),
            "T10YIE": points(2.2, 2.5),
            "VIXCLS": points(18, 40),
        })
        self.assertEqual(evaluate(data)["regime"], "H2")

    def test_missing_data_is_indeterminate(self):
        result = evaluate({})
        self.assertEqual(result["regime"], "INDETERMINATE")
        self.assertEqual(len(result["methodology"]["sha256"]), 64)

    def test_capex_metric_aggregates_at_least_three_companies(self):
        data = {
            "CAPEX_MSFT": points(40, 50),
            "CAPEX_GOOG": points(35, 45),
            "CAPEX_AMZN": points(48, 60),
        }
        metric = next(item for item in derived_metrics(data) if item["id"] == "AI_CAPEX_QUARTER")
        self.assertEqual(metric["value"], 155)

    def test_public_and_gross_debt_are_not_conflated(self):
        data = {
            "US_DEBT_HELD_PUBLIC": points(31_000_000, 32_000_000),
            "GFDEBTN": points(39_000_000, 40_000_000),
            "GDP": points(31_000, 32_000),
        }
        metrics = {item["id"]: item for item in derived_metrics(data)}
        self.assertEqual(metrics["US_PUBLIC_DEBT_GDP"]["value"], 100.0)
        self.assertEqual(metrics["US_GROSS_DEBT_GDP"]["value"], 125.0)


if __name__ == "__main__":
    unittest.main()
