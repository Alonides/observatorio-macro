import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.debt_nok_v1.fast_bridge import RULES
from observatorio.debt_nok_v1.fast_config import FX_CALIBRATION, configure_v103_rules


class FastConfigTests(unittest.TestCase):
    def test_direct_fx_thresholds_are_explicit_and_only_touch_fx_rules(self):
        configured = configure_v103_rules(RULES)
        original = {rule.target: rule for rule in RULES}
        changed = {rule.target: rule for rule in configured}
        for target, values in FX_CALIBRATION.items():
            self.assertEqual(changed[target].minimum_correlation, values["minimum_correlation"])
            self.assertEqual(changed[target].maximum_mae_pct, values["maximum_mae_pct"])
        self.assertEqual(
            changed["DTWEXBGS"].minimum_correlation,
            original["DTWEXBGS"].minimum_correlation,
        )
        self.assertEqual(
            changed["DCOILBRENTEU"].maximum_mae_pct,
            original["DCOILBRENTEU"].maximum_mae_pct,
        )


if __name__ == "__main__":
    unittest.main()
