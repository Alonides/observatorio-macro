import math
import unittest
from datetime import date, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.debt_nok_v1.fast_alignment import tracking_statistics_aligned


def business_days(count: int, start: date = date(2026, 1, 5)) -> list[date]:
    output = []
    current = start
    while len(output) < count:
        if current.weekday() < 5:
            output.append(current)
        current += timedelta(days=1)
    return output


class FastAlignmentTests(unittest.TestCase):
    def test_one_business_day_publication_shift_is_identified(self):
        days = business_days(45)
        official_values = [100.0]
        for index in range(1, 44):
            move = 0.001 * math.sin(index / 2.7) + 0.0007 * math.cos(index / 5.1)
            official_values.append(official_values[-1] * math.exp(move))
        official = [
            {"date": day.isoformat(), "value": value}
            for day, value in zip(days[:44], official_values)
        ]
        # The proxy labels the same sequence one business day later.
        proxy = [
            {"date": day.isoformat(), "value": value * 0.1}
            for day, value in zip(days[1:45], official_values)
        ]
        result = tracking_statistics_aligned(official, proxy)
        self.assertEqual(result["proxy_lag_business_days"], 1)
        self.assertGreater(result["correlation"], 0.999)
        self.assertLess(result["mae_pct_points"], 0.001)


if __name__ == "__main__":
    unittest.main()
