import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(module_name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


fueling_analysis = _load_module("fueling_analysis_sprint_script", "scripts/fueling_analysis.py")


class SprintIntervalDetectionTests(unittest.TestCase):
    def test_detects_standalone_short_sprints(self):
        for summary in ("6x 6s 650w", "4x 20s 520w", "8x 10s 600w", "3x 30s 450w"):
            with self.subTest(summary=summary):
                self.assertTrue(fueling_analysis._has_sprint_intervals(summary))

    def test_ignores_seconds_that_belong_to_a_minute_duration(self):
        for summary in ("3x 5m26s 207w", "5x 2m10s 310w", "2x 20m 230w"):
            with self.subTest(summary=summary):
                self.assertFalse(fueling_analysis._has_sprint_intervals(summary))

    def test_ignores_long_second_only_efforts(self):
        self.assertFalse(fueling_analysis._has_sprint_intervals("4x 45s 380w"))


class ClassifyRideSprintTests(unittest.TestCase):
    def test_z2_ride_with_embedded_6s_sprints_is_endurance_with_sprint(self):
        activity = {
            "duration_hours": 1.5,
            "z1_z2_pct": 90,
            "z3_z4_pct": 4,
            "z5_plus_pct": 2,
            "interval_summary": ["6x 6s 650w"],
            "tags": ["aerobic-threshold-moderate"],
        }
        self.assertEqual(fueling_analysis.classify_ride(activity), "endurance_with_sprint")

    def test_vo2_session_with_minute_second_durations_stays_vo2(self):
        activity = {
            "duration_hours": 1.2,
            "z1_z2_pct": 60,
            "z3_z4_pct": 15,
            "z5_plus_pct": 12,
            "interval_summary": ["5x 2m16s 330w"],
            "tags": [],
        }
        self.assertEqual(fueling_analysis.classify_ride(activity), "vo2")


if __name__ == "__main__":
    unittest.main()
