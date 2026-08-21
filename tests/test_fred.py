import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.fred import SourceError, parse_fred_csv


class FredParserTests(unittest.TestCase):
    def test_parses_date_header(self):
        text = "DATE,DGS10\n2026-08-19,4.31\n2026-08-20,.\n"
        self.assertEqual(parse_fred_csv(text, "DGS10"), [{"date": "2026-08-19", "value": 4.31}])

    def test_parses_observation_date_header(self):
        text = "observation_date,SOFR\n2026-08-20,3.65\n"
        self.assertEqual(parse_fred_csv(text, "SOFR")[-1]["value"], 3.65)

    def test_rejects_empty_numeric_series(self):
        with self.assertRaises(SourceError):
            parse_fred_csv("DATE,DGS10\n2026-08-20,.\n", "DGS10")


if __name__ == "__main__":
    unittest.main()

