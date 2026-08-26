import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.backtest import run_continuous_backtest
from observatorio.scenarios import us_rejection


class BacktestTests(unittest.TestCase):
    def test_continuous_backtest_returns_block_summaries(self):
        result = run_continuous_backtest(us_rejection())
        self.assertEqual(result["model_version"], "0.3.0")
        self.assertIn("urp", result["blocks"])
        self.assertGreater(result["blocks"]["urp"]["scored_sessions"], 0)
        self.assertGreaterEqual(result["blocks"]["urp"]["max_score"], 50.0)


if __name__ == "__main__":
    unittest.main()
