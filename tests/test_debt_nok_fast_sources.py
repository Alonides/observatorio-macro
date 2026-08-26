import unittest
from datetime import date

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.debt_nok_v1.fast_sources import (
    build_eia_cme_wti_proxy,
    parse_cme_wti_settlement,
)


class FastSourceTests(unittest.TestCase):
    def test_parse_cme_front_valid_settlement(self):
        payload = {
            "updateTime": "08/25/2026 06:00 PM CT",
            "settlements": [
                {"month": "SEP 26", "settle": "64.53A"},
                {"month": "OCT 26", "settle": "63.87"},
            ],
        }
        point = parse_cme_wti_settlement(payload, date(2026, 8, 25))
        self.assertIsNotNone(point)
        self.assertEqual(point["date"], "2026-08-25")
        self.assertEqual(point["contract"], "SEP 26")
        self.assertAlmostEqual(point["value"], 64.53)

    def test_hybrid_keeps_eia_history_and_appends_scaled_cme_tail(self):
        eia = [
            {"date": "2026-08-14", "value": 65.0},
            {"date": "2026-08-17", "value": 66.0},
            {"date": "2026-08-18", "value": 67.0},
        ]
        cme = [
            {"date": "2026-08-17", "value": 64.0},
            {"date": "2026-08-18", "value": 65.0},
            {"date": "2026-08-19", "value": 66.3},
            {"date": "2026-08-20", "value": 67.6},
        ]
        hybrid, metadata = build_eia_cme_wti_proxy(eia, cme)
        self.assertEqual(hybrid[:3], eia)
        self.assertEqual(metadata["cme_anchor"], "2026-08-18")
        self.assertEqual(metadata["appended_observations"], 2)
        self.assertEqual(hybrid[-1]["date"], "2026-08-20")
        self.assertAlmostEqual(hybrid[-1]["value"], 67.0 * 67.6 / 65.0)

    def test_hybrid_rejects_old_anchor(self):
        eia = [{"date": "2026-08-20", "value": 67.0}]
        cme = [
            {"date": "2026-08-14", "value": 65.0},
            {"date": "2026-08-21", "value": 66.0},
        ]
        with self.assertRaisesRegex(Exception, "anchor gap"):
            build_eia_cme_wti_proxy(eia, cme, maximum_anchor_gap_days=2)


if __name__ == "__main__":
    unittest.main()
