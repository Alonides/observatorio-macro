import math
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.debt_nok_v1.fast_bridge import (
    build_fast_lane_payload,
    build_fast_series,
    parse_ecb_reference_xml,
)


def business_days(count: int, start: date = date(2026, 6, 1)) -> list[str]:
    output = []
    current = start
    while len(output) < count:
        if current.weekday() < 5:
            output.append(current.isoformat())
        current += timedelta(days=1)
    return output


def points(days, values):
    return [{"date": day, "value": value} for day, value in zip(days, values)]


def operational(level: str, nks_score: float = 0.0) -> dict:
    blocks = {
        "URP": {"score": 0.0, "state": "inactive", "asof": "2026-08-25"},
        "URR": {"score": 0.0, "state": "inactive", "asof": "2026-08-25"},
        "DSS": {"score": 0.0, "state": "inactive", "asof": "2026-08-25"},
        "NKS": {"score": nks_score, "state": "stress" if nks_score else "normal", "asof": "2026-08-25"},
        "NRS": {"score": 0.0, "state": "inactive", "asof": "2026-08-25"},
    }
    return {
        "asof": "2026-08-25",
        "block_asof": {key: "2026-08-25" for key in blocks},
        "freshness": {"quality": "fresh"},
        "operational": {"level": level, "blocks": blocks},
    }


class FastBridgeTests(unittest.TestCase):
    def test_ecb_parser_derives_required_crosses(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <Envelope><Cube><Cube>
          <Cube time="2026-08-24">
            <Cube currency="USD" rate="1.20"/><Cube currency="JPY" rate="180"/>
            <Cube currency="GBP" rate="0.80"/><Cube currency="CAD" rate="1.60"/>
            <Cube currency="SEK" rate="12.00"/><Cube currency="CHF" rate="0.96"/>
            <Cube currency="NOK" rate="12.60"/>
          </Cube>
          <Cube time="2026-08-25">
            <Cube currency="USD" rate="1.25"/><Cube currency="JPY" rate="187.5"/>
            <Cube currency="GBP" rate="0.82"/><Cube currency="CAD" rate="1.65"/>
            <Cube currency="SEK" rate="12.25"/><Cube currency="CHF" rate="0.98"/>
            <Cube currency="NOK" rate="12.75"/>
          </Cube>
        </Cube></Cube></Envelope>"""
        parsed = parse_ecb_reference_xml(xml)
        self.assertEqual(len(parsed["ECB_DEXUSEU"]), 2)
        self.assertAlmostEqual(parsed["ECB_DEXUSEU"][-1]["value"], 1.25)
        self.assertAlmostEqual(parsed["ECB_DEXNOUS"][-1]["value"], 12.75 / 1.25)
        self.assertAlmostEqual(parsed["ECB_DEXSDUS"][-1]["value"], 12.25 / 1.25)
        self.assertGreater(parsed["ECB_DOLLAR_PROXY"][-1]["value"], 0.0)

    def test_bridge_appends_future_proxy_returns_without_overwriting_official(self):
        days = business_days(45)
        official_values = [100.0 * math.exp(0.001 * index) for index in range(40)]
        proxy_values = [10.0 * math.exp(0.001 * index) for index in range(45)]
        official = points(days[:40], official_values)
        proxies = {"ECB_DEXUSEU": points(days, proxy_values)}

        extended, metadata = build_fast_series({"DEXUSEU": official}, proxies=proxies)
        target = metadata["targets"]["DEXUSEU"]
        self.assertEqual(target["status"], "active")
        self.assertEqual(target["bridge_observations"], 5)
        self.assertEqual(len(extended["DEXUSEU"]), 45)
        self.assertEqual(extended["DEXUSEU"][:40], official)
        expected = official_values[-1] * proxy_values[-1] / proxy_values[39]
        self.assertAlmostEqual(extended["DEXUSEU"][-1]["value"], expected)

    def test_bad_tracking_proxy_is_rejected(self):
        days = business_days(45)
        official_values = [100.0 * math.exp(0.002 * index) for index in range(40)]
        proxy_values = [10.0 * math.exp(-0.002 * index) for index in range(45)]
        extended, metadata = build_fast_series(
            {"DEXUSEU": points(days[:40], official_values)},
            proxies={"ECB_DEXUSEU": points(days, proxy_values)},
        )
        target = metadata["targets"]["DEXUSEU"]
        self.assertEqual(target["status"], "rejected")
        self.assertEqual(target["reason"], "tracking_correlation_below_threshold")
        self.assertEqual(len(extended["DEXUSEU"]), 40)

    def test_provisional_escalation_requires_human_review(self):
        bridge = {
            "available": True,
            "active_targets": ["DEXNOUS"],
            "targets": {"DEXNOUS": {"bridge_end": "2026-08-25"}},
        }
        payload = build_fast_lane_payload(
            operational("normal"),
            operational("alert", nks_score=70.0),
            bridge,
        )
        self.assertTrue(payload["divergence"])
        self.assertTrue(payload["review_required"])
        self.assertEqual(payload["level"], "alert")
        self.assertEqual(payload["official_level"], "normal")
        self.assertEqual(payload["comparisons"]["NKS"]["delta"], 70.0)

    def test_provisional_critical_is_visually_capped_at_alert(self):
        bridge = {
            "available": True,
            "active_targets": ["DTWEXBGS"],
            "targets": {"DTWEXBGS": {"bridge_end": "2026-08-25"}},
        }
        payload = build_fast_lane_payload(
            operational("normal"),
            operational("critical", nks_score=90.0),
            bridge,
        )
        self.assertEqual(payload["raw_provisional_level"], "critical")
        self.assertEqual(payload["level"], "alert")
        self.assertTrue(payload["review_required"])


if __name__ == "__main__":
    unittest.main()
