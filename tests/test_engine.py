import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.engine import evaluate


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


if __name__ == "__main__":
    unittest.main()

