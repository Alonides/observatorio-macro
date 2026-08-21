import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.derive import _asof_binary, derive_series


class DerivedSeriesTests(unittest.TestCase):
    def test_asof_alignment_does_not_look_into_the_future(self):
        left = [{"date": "2026-08-21", "value": 200}]
        right = [
            {"date": "2026-08-20", "value": 10},
            {"date": "2026-08-22", "value": 20},
        ]
        self.assertEqual(_asof_binary(left, right, lambda a, b: a / b), [
            {"date": "2026-08-21", "value": 20.0},
        ])

    def test_gold_formulas(self):
        series = {
            "GOLDAMGBD228NLBM": [{"date": "2026-08-20", "value": 4000}],
            "CBBTCUSD": [{"date": "2026-08-20", "value": 120000}],
            "DEXNOUS": [{"date": "2026-08-20", "value": 10}],
            "DEXUSEU": [{"date": "2026-08-20", "value": 1.25}],
            "US_DEBT_HELD_PUBLIC": [{"date": "2026-08-20", "value": 32_000_000}],
        }
        derived = derive_series(series)
        self.assertEqual(derived["BTC_XAU"][-1]["value"], 30)
        self.assertEqual(derived["XAU_NOK"][-1]["value"], 40_000)
        self.assertEqual(derived["XAU_EUR"][-1]["value"], 3200)
        self.assertEqual(derived["US_PUBLIC_DEBT_XAU"][-1]["value"], 8000)


if __name__ == "__main__":
    unittest.main()
