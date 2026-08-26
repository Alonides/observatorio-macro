import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.debt_nok_v1.fast_shapes import parse_dated_price_payload


class FastShapeTests(unittest.TestCase):
    def test_parallel_arrays(self):
        payload = {
            "dates": ["2026-08-21", "2026-08-25"],
            "prices": [84.2, 85.1],
        }
        self.assertEqual(parse_dated_price_payload(payload), [
            {"date": "2026-08-21", "value": 84.2},
            {"date": "2026-08-25", "value": 85.1},
        ])

    def test_date_keyed_mapping(self):
        payload = {"history": {"2026-08-21": 84.2, "2026-08-25": 85.1}}
        self.assertEqual(parse_dated_price_payload(payload), [
            {"date": "2026-08-21", "value": 84.2},
            {"date": "2026-08-25", "value": 85.1},
        ])

    def test_pair_rows(self):
        payload = {"data": [["2026-08-21", 84.2], ["2026-08-25", 85.1]]}
        self.assertEqual(parse_dated_price_payload(payload), [
            {"date": "2026-08-21", "value": 84.2},
            {"date": "2026-08-25", "value": 85.1},
        ])


if __name__ == "__main__":
    unittest.main()
