import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.debt_nok_v1.fast_fallbacks import (
    parse_americas_brent,
    parse_yahoo_chart,
)


class FastFallbackTests(unittest.TestCase):
    def test_americas_parser_accepts_nested_history_shape(self):
        payload = {
            "source": "Stooq cb.f",
            "data": {
                "history": [
                    {"date": "2026-08-21", "close": 84.2},
                    {"period": "2026-08-22", "value": None},
                    {"date": "2026-08-25", "price": "85.10"},
                ]
            },
        }
        self.assertEqual(parse_americas_brent(payload), [
            {"date": "2026-08-21", "value": 84.2},
            {"date": "2026-08-25", "value": 85.1},
        ])

    def test_americas_parser_accepts_unix_timestamp(self):
        timestamp = int(datetime(2026, 8, 26, tzinfo=timezone.utc).timestamp())
        payload = {"latest": {"timestamp": timestamp, "brent": 86.25}}
        self.assertEqual(parse_americas_brent(payload), [
            {"date": "2026-08-26", "value": 86.25},
        ])

    def test_yahoo_chart_parser_skips_null_closes(self):
        timestamps = [
            int(datetime(2026, 8, 21, tzinfo=timezone.utc).timestamp()),
            int(datetime(2026, 8, 24, tzinfo=timezone.utc).timestamp()),
            int(datetime(2026, 8, 25, tzinfo=timezone.utc).timestamp()),
        ]
        payload = {
            "chart": {
                "error": None,
                "result": [{
                    "timestamp": timestamps,
                    "indicators": {"quote": [{"close": [84.2, None, 85.1]}]},
                }],
            }
        }
        points = parse_yahoo_chart(payload)
        self.assertEqual(points, [
            {"date": "2026-08-21", "value": 84.2},
            {"date": "2026-08-25", "value": 85.1},
        ])

    def test_yahoo_chart_parser_rejects_error_payload(self):
        payload = {"chart": {"result": None, "error": {"code": "Not Found"}}}
        with self.assertRaisesRegex(Exception, "Yahoo chart error"):
            parse_yahoo_chart(payload)


if __name__ == "__main__":
    unittest.main()
