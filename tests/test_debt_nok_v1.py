import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.debt_nok_v04.scenarios import (
    dollar_shortage,
    false_usdnok_reversal,
    norwegian_reversal_confirmed,
    us_rejection,
    us_rejection_regime,
)
from observatorio.debt_nok_v1.monitor import MODEL_VERSION, evaluate_operational
from observatorio.debt_nok_v1.report import build_report


class DebtNokV1Tests(unittest.TestCase):
    def test_v1_preserves_core_and_adds_operational_layer(self):
        result = evaluate_operational(us_rejection())
        self.assertEqual(result["model_version"], MODEL_VERSION)
        self.assertEqual(result["core_model_version"], "0.4.1")
        self.assertIn(result["operational"]["level"], {"watch", "alert"})
        self.assertIn("URP", result["operational"]["blocks"])

    def test_persistent_rejection_is_critical(self):
        result = evaluate_operational(us_rejection_regime())
        self.assertEqual(result["operational"]["level"], "critical")
        self.assertTrue(result["operational"]["notification_required"])

    def test_dollar_shortage_is_not_called_us_rejection(self):
        result = evaluate_operational(dollar_shortage())
        self.assertEqual(result["operational"]["blocks"]["URP"]["score"], 0.0)
        self.assertGreaterEqual(result["operational"]["blocks"]["DSS"]["score"], 50.0)

    def test_inactive_nrs_has_zero_operational_score(self):
        result = evaluate_operational(false_usdnok_reversal())
        nrs = result["nrs"]
        self.assertEqual(nrs["state"], "inactive")
        self.assertEqual(nrs["operational_score"], 0.0)
        self.assertIsNotNone(nrs["gate_score"])

    def test_confirmed_nrs_is_material_alert_not_critical_loss_signal(self):
        result = evaluate_operational(norwegian_reversal_confirmed())
        self.assertEqual(result["nrs"]["state"], "confirmed")
        self.assertEqual(result["operational"]["level"], "alert")
        self.assertTrue(result["operational"]["notification_required"])
        self.assertIn("cambio de régimen", " ".join(result["operational"]["reasons"]))

    def test_report_is_deterministic_and_spanish(self):
        report = build_report(us_rejection(), mode="weekly", generated_at="2026-08-26T10:00:00+00:00")
        self.assertEqual(report["model_version"], MODEL_VERSION)
        self.assertEqual(report["mode"], "weekly")
        self.assertIn("# Informe Debt/NOK", report["markdown"])
        self.assertIn("Panel de bloques", report["markdown"])
        self.assertIn("score_deltas_5_sessions", report)


if __name__ == "__main__":
    unittest.main()
