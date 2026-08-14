import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cognitive_map import CognitiveMap


class CognitiveMapTests(unittest.TestCase):
    def setUp(self):
        self.map = CognitiveMap(confidence_threshold=0.6, accuracy_threshold=0.6)

    def test_classifies_all_confidence_accuracy_quadrants(self):
        self.assertEqual(self.map.classify(0.8, 0.8), "KNOWN_KNOWN")
        self.assertEqual(self.map.classify(0.8, 0.2), "UNKNOWN_KNOWN")
        self.assertEqual(self.map.classify(0.2, 0.8), "KNOWN_UNKNOWN")
        self.assertEqual(self.map.classify(0.2, 0.2), "UNKNOWN_UNKNOWN")

    def test_tracks_danger_zone_for_overconfident_failures(self):
        self.map.update("finance", "forecast", confidence=0.9, accuracy=0.2)

        summary = self.map.get_summary()

        self.assertEqual(summary["quadrant_distribution"]["UNKNOWN_KNOWN"], 1)
        self.assertEqual(summary["danger_zones"][0]["domain"], "finance")


if __name__ == "__main__":
    unittest.main()