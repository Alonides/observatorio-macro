import json
import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.methodology import load_methodology, manifest, methodology_hash


class MethodologyTests(unittest.TestCase):
    def test_manifest_is_stable_and_json_serializable(self):
        payload = load_methodology()
        first = methodology_hash(payload)
        second = methodology_hash(load_methodology())
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)
        json.dumps(manifest(payload))

    def test_canonical_hypothesis_mapping(self):
        hypotheses = load_methodology()["hypotheses"]
        self.assertIn("oferta", hypotheses["H0"]["title"].lower())
        self.assertIn("confianza", hypotheses["H1"]["title"].lower())
        self.assertIn("global", hypotheses["H2"]["title"].lower())

    def test_context_windows_cannot_classify(self):
        event = load_methodology()["event_engine"]
        self.assertFalse(event["context_windows_are_classifiers"])

    def test_relative_model_is_calibrated_and_artifact_is_pinned(self):
        target = load_methodology()["event_engine"]["us_specific"]["target_model"]
        self.assertEqual(target["status"], "calibrated_candidate")
        self.assertGreater(
            float(target["calibration_result"]["h1_p95_pp"]),
            float(target["calibration_result"]["h0_p90_pp"]),
        )
        artifact = Path(__file__).resolve().parents[1] / target["artifact"]
        self.assertTrue(artifact.exists())
        self.assertEqual(hashlib.sha256(artifact.read_bytes()).hexdigest(), target["artifact_sha256"])


if __name__ == "__main__":
    unittest.main()
