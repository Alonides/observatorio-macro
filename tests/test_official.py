import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.official import parse_fed_ddp_csv, parse_sofr_json, parse_treasury_csv


class OfficialSourceParserTests(unittest.TestCase):
    def test_treasury_csv(self):
        text = 'Date,"2 Yr","10 Yr"\n08/20/2026,4.19,4.69\n'
        parsed = parse_treasury_csv(text)
        self.assertEqual(parsed["10 Yr"], [{"date": "2026-08-20", "value": 4.69}])

    def test_fed_ddp_csv_skips_metadata(self):
        text = '\n'.join([
            '"Series Description","Nominal Broad Dollar Index"',
            '"Unit:","Index"',
            '"Time Period","JRXWTFB_N.B"',
            '2026-08-13,119.1848',
            '2026-08-14,ND',
        ])
        parsed = parse_fed_ddp_csv(text)
        self.assertEqual(parsed["JRXWTFB_N.B"][-1]["value"], 119.1848)

    def test_sofr_json(self):
        payload = {"refRates": [{"effectiveDate": "2026-08-20", "percentRate": 3.63}]}
        self.assertEqual(parse_sofr_json(payload), [{"date": "2026-08-20", "value": 3.63}])


if __name__ == "__main__":
    unittest.main()

