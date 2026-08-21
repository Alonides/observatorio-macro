import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.state_engine import evaluate_state


class StateEngineTests(unittest.TestCase):
    def test_state_never_returns_an_aggregate_score(self):
        result = evaluate_state({})
        self.assertIsNone(result["aggregate_score"])
        self.assertIsNone(result["aggregate_label"])
        self.assertEqual(result["engine"], "structural_state")

    def test_public_debt_and_interest_burden(self):
        data = {
            "US_DEBT_HELD_PUBLIC": [{"date": "2026-08-20", "value": 32_000_000}],
            "GFDEBTN": [{"date": "2026-08-20", "value": 40_000_000}],
            "GDP": [{"date": "2026-06-30", "value": 32_000}],
            "A091RC1Q027SBEA": [{"date": "2026-06-30", "value": 1024}],
        }
        dimensions = {item["key"]: item for item in evaluate_state(data)["dimensions"]}
        self.assertEqual(dimensions["debt_held_by_public_to_gdp"]["value"], 100.0)
        self.assertEqual(dimensions["debt_held_by_public_to_gdp"]["gross_debt_context_pct"], 125.0)
        self.assertEqual(dimensions["interest_burden"]["value"], 3.2)


if __name__ == "__main__":
    unittest.main()
