import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.engine import derived_metrics, evaluate
from observatorio.methodology import load_methodology


AS_OF = date(2026, 8, 20)
TARGET = load_methodology()["event_engine"]["us_specific"]["target_model"]
FIT = TARGET["calibration_result"]


def points(old, new):
    return [{"date": "2026-05-01", "value": old}, {"date": "2026-08-20", "value": new}]


def peer_data(residual_pp=0.0, peer_change_pp=0.1):
    """Siete cierres mensuales más dato corriente para probar el modelo real."""
    peer_ids = ("IRLTLT01JPM156N", "IRLTLT01DEM156N", "IRLTLT01GBM156N")
    months = ("2026-01-30", "2026-02-27", "2026-03-31", "2026-04-30", "2026-05-29", "2026-06-30", "2026-07-31")
    levels = {series_id: 2.0 for series_id in peer_ids}
    levels["DGS10"] = 4.0
    data = {series_id: [] for series_id in ("DGS10", *peer_ids)}
    for index, day in enumerate(months):
        if index:
            for series_id in peer_ids:
                levels[series_id] += peer_change_pp
            predicted = float(FIT["intercept_pp"]) + sum(
                float(FIT["betas"][series_id]) * peer_change_pp for series_id in peer_ids
            )
            residual = residual_pp[index - 1] if isinstance(residual_pp, (list, tuple)) else residual_pp
            levels["DGS10"] += predicted + residual
        for series_id in data:
            data[series_id].append({"date": day, "value": levels[series_id]})
    for series_id in data:
        data[series_id].append({"date": "2026-08-20", "value": levels[series_id]})
    return data


class EngineTests(unittest.TestCase):
    def test_h2_is_global_duration_not_h0(self):
        data = peer_data(residual_pp=0.0, peer_change_pp=0.15)
        result = evaluate(data, as_of=AS_OF)
        self.assertEqual(result["regime"], "H2")
        self.assertEqual(result["diagnostics"]["markets_rising"], 4)

    def test_h0_requires_positive_us_specific_evidence(self):
        data = peer_data(residual_pp=0.20, peer_change_pp=-0.05)
        result = evaluate(data, as_of=AS_OF)
        self.assertEqual(result["regime"], "H0")
        self.assertEqual(result["evidence_level"], "compatible")

    def test_absence_of_h1_does_not_prove_h0(self):
        self.assertEqual(evaluate({"DGS10": points(4.0, 4.4)}, as_of=AS_OF)["regime"], "INDETERMINATE")

    def test_h2_requires_relative_model_to_be_available(self):
        short = {
            series_id: points(2.0, 2.4)
            for series_id in ("DGS10", "IRLTLT01JPM156N", "IRLTLT01DEM156N", "IRLTLT01GBM156N")
        }
        result = evaluate(short, as_of=AS_OF)
        self.assertTrue(next(signal for signal in result["signals"] if signal["key"] == "global_duration")["active"])
        self.assertEqual(result["regime"], "INDETERMINATE")

    def test_h1_requires_triple_specificity_and_confirmation(self):
        data = peer_data(residual_pp=0.20, peer_change_pp=-0.05)
        data.update({
            "DTWEXBGS": points(100, 96),
            "DFII10": points(2.0, 2.4),
            "T10YIE": points(2.2, 2.5),
            "SOFR": points(3.5, 4.0),
            "IORB": points(3.5, 3.7),
        })
        result = evaluate(data, as_of=AS_OF)
        self.assertEqual(result["regime"], "H1")
        self.assertEqual(result["triple_active"], 3)
        self.assertEqual(result["evidence_level"], "candidate")

    def test_h1_requires_two_consecutive_months_above_p95(self):
        data = peer_data(residual_pp=[0, 0, 0, 0, 0, 0.40], peer_change_pp=-0.05)
        data.update({
            "DTWEXBGS": points(100, 96),
            "DFII10": points(2.0, 2.4),
            "T10YIE": points(2.2, 2.5),
            "SOFR": points(3.5, 4.0),
            "IORB": points(3.5, 3.7),
        })
        result = evaluate(data, as_of=AS_OF)
        relative = result["diagnostics"]["us_relative_model"]
        self.assertTrue(relative["h0_specific"])
        self.assertFalse(relative["h1_specific_persistent"])
        self.assertNotEqual(result["regime"], "H1")

    def test_mixed_is_reachable(self):
        data = peer_data(residual_pp=0.20, peer_change_pp=0.05)
        data.update({
            "DTWEXBGS": points(100, 96),
            "DFII10": points(2.0, 2.4),
            "T10YIE": points(2.2, 2.5),
            "VIXCLS": points(18, 40),
        })
        self.assertEqual(evaluate(data, as_of=AS_OF)["regime"], "MIXED")

    def test_reflation_signature_is_context_not_h1_verdict(self):
        data = peer_data(residual_pp=0.0, peer_change_pp=0.15)
        data.update({
            "DTWEXBGS": points(100, 96),
            "DFII10": points(2.0, 2.4),
            "T10YIE": points(2.2, 2.5),
            "SP500": points(1000, 1120),
            "BAMLC0A0CM": points(3.0, 2.0),
        })
        result = evaluate(data, as_of=AS_OF)
        self.assertNotEqual(result["regime"], "H1")
        self.assertEqual(result["risk_context"]["classification"], "REFLATION_COMPATIBLE")
        self.assertEqual(result["context"], "TRIPLE_ALERT")

    def test_vix_without_us_specificity_cannot_create_h1(self):
        data = peer_data(residual_pp=0.0, peer_change_pp=0.15)
        data.update({
            "DTWEXBGS": points(100, 96),
            "DFII10": points(2.0, 2.4),
            "T10YIE": points(2.2, 2.5),
            "VIXCLS": points(18, 40),
        })
        self.assertEqual(evaluate(data, as_of=AS_OF)["regime"], "H2")

    def test_missing_data_is_indeterminate(self):
        result = evaluate({}, as_of=AS_OF)
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
