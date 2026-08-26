import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Importing the package installs the presentation-only terminology patch.
import observatorio.debt_nok_v1  # noqa: F401
from observatorio.debt_nok_v1.fast_bridge import build_fast_lane_payload
from observatorio.debt_nok_v1.report import render_markdown


def _result(level="normal"):
    blocks = {
        key: {"score": 0.0, "state": "inactive", "asof": "2026-08-25"}
        for key in ("URP", "URR", "DSS", "NKS", "NRS")
    }
    return {
        "asof": "2026-08-25",
        "operational": {"level": level, "blocks": blocks},
    }


class SourceTerminologyTests(unittest.TestCase):
    def test_fast_lane_disclaimer_distinguishes_secondary_sources(self):
        bridge = {
            "available": True,
            "active_targets": ["DCOILBRENTEU"],
            "targets": {"DCOILBRENTEU": {"bridge_end": "2026-08-26"}},
            "method": "Returns from faster official proxy series are spliced to the last official level.",
        }
        payload = build_fast_lane_payload(_result(), _result(), bridge)
        self.assertIn("primarios o secundarios", payload["disclaimer"])
        self.assertNotIn("proxies oficiales", payload["disclaimer"])
        self.assertIn("explicitly labelled secondary", payload["bridge"]["method"])

    def test_markdown_rewrites_legacy_generic_wording(self):
        report = {
            "report_date": "2026-08-26",
            "generated_at": "2026-08-26T14:00:00+00:00",
            "generated_at_oslo": "2026-08-26T16:00:00+02:00",
            "asof": "2026-08-25",
            "headline": "Normal",
            "summary": "Sin señales.",
            "reasons": ["Ningún bloque supera umbrales"],
            "alert": {"label": "Normal"},
            "freshness": {"blocks": {}},
            "current": {
                "operational": {
                    "level": "normal",
                    "blocks": {
                        key: {
                            "label": key,
                            "score": 0.0,
                            "state": "inactive",
                            "asof": "2026-08-25",
                        }
                        for key in ("URP", "URR", "DSS", "NKS", "NRS")
                    },
                },
                "urp": {"values": {}},
                "nks": {"values": {}},
            },
            "previous": {
                "operational": {
                    "blocks": {
                        key: {"score": 0.0}
                        for key in ("URP", "URR", "DSS", "NKS", "NRS")
                    }
                }
            },
            "score_deltas_5_sessions": {
                key: 0.0 for key in ("URP", "URR", "DSS", "NKS", "NRS")
            },
            "fast_lane": {
                "label": "Provisional",
                "message": "Sin divergencia.",
                "disclaimer": "La vía rápida usa proxies oficiales correlacionados.",
                "comparisons": {},
                "bridge": {},
            },
        }
        markdown = render_markdown(report)
        self.assertNotIn("proxies oficiales", markdown)
        self.assertIn("primarios o secundarios", markdown)


if __name__ == "__main__":
    unittest.main()
