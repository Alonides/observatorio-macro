import sys
import unittest
import json
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.calibration import (
    MODEL_SERIES,
    activation_report,
    fit_ols,
    live_relative_score,
    month_end_rows,
    monthly_changes,
    nearest_rank,
    residual_rows,
    rolling_residuals,
    verify_artifact,
)
from observatorio.methodology import load_methodology


def synthetic_levels(months=30):
    series = {series_id: [] for series_id in MODEL_SERIES}
    levels = {series_id: 2.0 for series_id in MODEL_SERIES}
    for index in range(months):
        year = 2023 + index // 12
        month = index % 12 + 1
        day = f"{year:04d}-{month:02d}-28"
        jp = ((index % 5) - 2) * 0.03
        de = ((index % 7) - 3) * 0.02
        uk = ((index % 4) - 1.5) * 0.04
        changes = {
            "IRLTLT01JPM156N": jp,
            "IRLTLT01DEM156N": de,
            "IRLTLT01GBM156N": uk,
            "DGS10": 0.01 + 0.2 * jp + 0.5 * de + 0.3 * uk,
        }
        if index:
            for series_id, change in changes.items():
                levels[series_id] += change
        for series_id in MODEL_SERIES:
            series[series_id].append({"date": day, "value": levels[series_id]})
    return series


class CalibrationTests(unittest.TestCase):
    def test_month_end_alignment_uses_last_observation_and_no_imputation(self):
        series = synthetic_levels(14)
        series["DGS10"].append({"date": "2024-02-29", "value": 9.0})
        rows = month_end_rows(series, "2024-02")
        self.assertEqual(rows[-1]["levels"]["DGS10"], 9.0)
        self.assertEqual(rows[-1]["observation_dates"]["DGS10"], "2024-02-29")

    def test_ols_recovers_known_coefficients(self):
        changes = monthly_changes(month_end_rows(synthetic_levels()))
        fit = fit_ols(changes)
        self.assertAlmostEqual(fit["intercept"], 0.01, places=9)
        self.assertAlmostEqual(fit["betas"]["IRLTLT01JPM156N"], 0.2, places=9)
        self.assertAlmostEqual(fit["betas"]["IRLTLT01DEM156N"], 0.5, places=9)
        self.assertAlmostEqual(fit["betas"]["IRLTLT01GBM156N"], 0.3, places=9)

    def test_nearest_rank_is_explicit_and_reproducible(self):
        self.assertEqual(nearest_rank(list(range(1, 11)), 90), 9)
        self.assertEqual(nearest_rank(list(range(1, 11)), 95), 10)

    def test_rolling_scores_do_not_bridge_missing_months(self):
        rows = [
            {"month": "2026-01", "residual_pp": 0.1},
            {"month": "2026-02", "residual_pp": 0.2},
            {"month": "2026-04", "residual_pp": 0.3},
        ]
        self.assertEqual(rolling_residuals(rows, 3), [])

    def test_persistence_requires_consecutive_scores(self):
        scores = [
            {"month": "2026-01", "residual_sum_pp": 1.0},
            {"month": "2026-02", "residual_sum_pp": 1.1},
            {"month": "2026-04", "residual_sum_pp": 1.2},
        ]
        report = activation_report(scores, 0.8, 0.9)
        self.assertEqual(report["persistent_p95_months"], ["2026-02"])

    def test_live_score_requires_closed_month_and_two_month_persistence(self):
        series = synthetic_levels(30)
        target = {
            "classifier": {"horizon_months": 3},
            "h1_persistence_months": 2,
            "calibration_result": {
                "intercept_pp": 0.01,
                "betas": {
                    "IRLTLT01JPM156N": 0.2,
                    "IRLTLT01DEM156N": 0.5,
                    "IRLTLT01GBM156N": 0.3,
                },
                "h0_p90_pp": -0.001,
                "h1_p95_pp": -0.001,
            },
        }
        result = live_relative_score(series, target, date(2025, 7, 15))
        self.assertTrue(result["available"])
        self.assertEqual(result["month"], "2025-06")
        self.assertTrue(result["h1_specific_persistent"])

    def test_frozen_artifact_rebuilds_exactly_offline(self):
        root = Path(__file__).resolve().parents[1]
        target = load_methodology()["event_engine"]["us_specific"]["target_model"]
        artifact = json.loads((root / target["artifact"]).read_text(encoding="utf-8"))
        verification = verify_artifact(artifact, target)
        self.assertTrue(verification["valid"], verification["mismatched_sections"])


if __name__ == "__main__":
    unittest.main()
