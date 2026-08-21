import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datetime import date

from observatorio.pipeline import _merge_points, _not_after


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
            {"date": "2026-08-19", "value": 4.25, "revision": 1},
            {"date": "2026-08-20", "value": 4.3, "revision": 0},
        ])

    def test_merge_applies_retention_limit(self):
        points = [{"date": f"2026-08-{day:02d}", "value": day} for day in range(1, 6)]
        self.assertEqual(_merge_points([], points, 2), [
            {"date": "2026-08-04", "value": 4, "revision": 0},
            {"date": "2026-08-05", "value": 5, "revision": 0},
        ])

    def test_merge_preserves_first_retrieval_until_revision(self):
        previous = [{"date": "2026-08-20", "value": 4.3, "retrieved_at": "2026-08-20T06:00:00+00:00", "revision": 0}]
        unchanged = [{"date": "2026-08-20", "value": 4.3, "retrieved_at": "2026-08-21T06:00:00+00:00"}]
        self.assertEqual(
            _merge_points(previous, unchanged, 10)[0]["retrieved_at"],
            "2026-08-20T06:00:00+00:00",
        )

        revised = [{"date": "2026-08-20", "value": 4.4, "retrieved_at": "2026-08-22T06:00:00+00:00"}]
        merged = _merge_points(previous, revised, 10)[0]
        self.assertEqual(merged["revision"], 1)
        self.assertEqual(merged["retrieved_at"], "2026-08-22T06:00:00+00:00")

    def test_future_periods_are_never_published_as_observed(self):
        points = [
            {"date": "2026-08-20", "value": 3.65},
            {"date": "2026-08-21", "value": 3.65},
            {"date": "2026-08-24", "value": 3.65},
        ]
        self.assertEqual(
            _not_after(points, date(2026, 8, 21)),
            points[:2],
        )


if __name__ == "__main__":
    unittest.main()
