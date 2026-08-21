import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.pipeline import _merge_points


class PipelineTests(unittest.TestCase):
    def test_merge_preserves_history_and_replaces_same_day(self):
        previous = [
            {"date": "2026-08-18", "value": 4.1},
            {"date": "2026-08-19", "value": 4.2},
        ]
        incoming = [
            {"date": "2026-08-19", "value": 4.25},
            {"date": "2026-08-20", "value": 4.3},
        ]
        self.assertEqual(_merge_points(previous, incoming, 10), [
            {"date": "2026-08-18", "value": 4.1},
            {"date": "2026-08-19", "value": 4.25},
            {"date": "2026-08-20", "value": 4.3},
        ])

    def test_merge_applies_retention_limit(self):
        points = [{"date": f"2026-08-{day:02d}", "value": day} for day in range(1, 6)]
        self.assertEqual(_merge_points([], points, 2), points[-2:])


if __name__ == "__main__":
    unittest.main()
