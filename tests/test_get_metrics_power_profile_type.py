"""Tests for power profile rider type classification in get_metrics.py."""

import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_get_metrics_module():
    module_path = REPO_ROOT / "scripts" / "get_metrics.py"
    spec = importlib.util.spec_from_file_location("get_metrics_script", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class PowerProfileTypeTests(unittest.TestCase):
    def test_sample_profile_is_all_rounder(self):
        module = _load_get_metrics_module()

        profile = {
            "p15s": {"watts": 469, "w_per_kg": 6.10},
            "p1min": {"watts": 330, "w_per_kg": 4.22},
            "p5min": {"watts": 292, "w_per_kg": 3.80},
            "p20min": {"watts": 247, "w_per_kg": 3.22},
            "curve_slope": -0.5361,
        }

        result = module._build_power_profile_type(profile)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["type"], "All Rounder")
        self.assertEqual(result["type_key"], "all_rounder")
        self.assertGreaterEqual(result["heuristic_score"], 0.2)

    def test_sprint_biased_profile_is_sprinter(self):
        module = _load_get_metrics_module()

        profile = {
            "p15s": {"watts": 1200, "w_per_kg": 15.0},
            "p1min": {"watts": 720, "w_per_kg": 9.0},
            "p5min": {"watts": 460, "w_per_kg": 5.8},
            "p20min": {"watts": 310, "w_per_kg": 3.9},
            "curve_slope": -0.42,
        }

        result = module._build_power_profile_type(profile)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["type"], "Sprinter")
        self.assertEqual(result["type_key"], "sprinter")

    def test_endurance_climbing_profile_is_climber(self):
        module = _load_get_metrics_module()

        profile = {
            "p15s": {"watts": 600, "w_per_kg": 7.0},
            "p1min": {"watts": 500, "w_per_kg": 5.8},
            "p5min": {"watts": 460, "w_per_kg": 5.3},
            "p20min": {"watts": 410, "w_per_kg": 4.7},
            "curve_slope": -0.62,
        }

        result = module._build_power_profile_type(profile)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["type"], "Climber")
        self.assertEqual(result["type_key"], "climber")


if __name__ == "__main__":
    unittest.main()
