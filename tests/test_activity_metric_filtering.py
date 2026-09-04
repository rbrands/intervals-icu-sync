import importlib.util
import unittest
from datetime import date, timedelta
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(module_name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


prepare_activities = _load_module(
    "prepare_activities_metric_filter_script",
    "scripts/prepare_activities_for_coach.py",
)
analyze_week = _load_module(
    "analyze_week_metric_filter_script",
    "scripts/analyze_week.py",
)


def _activity(**overrides) -> dict:
    activity = {
        "id": "i1",
        "type": "Ride",
        "source": "GARMIN",
        "start_date_local": date.today().isoformat() + "T09:00:00",
        "moving_time": 2450,
        "icu_training_load": None,
        "tags": ["lactate-threshold-moderate"],
    }
    activity.update(overrides)
    return activity


class ActivityMetricFilteringTests(unittest.TestCase):
    def test_tagged_activity_without_metrics_is_dropped(self):
        empty = _activity()

        self.assertEqual(prepare_activities.filter_activities([empty]), [])
        self.assertEqual(analyze_week.filter_activities([empty]), [])

    def test_tagged_activity_with_power_is_kept(self):
        with_power = _activity(icu_average_watts=210)

        self.assertEqual(len(prepare_activities.filter_activities([with_power])), 1)
        self.assertEqual(len(analyze_week.filter_activities([with_power])), 1)

    def test_tagged_activity_with_zone_times_is_kept(self):
        with_zones = _activity(icu_zone_times=[{"id": "Z2", "secs": 1800}])

        self.assertEqual(len(prepare_activities.filter_activities([with_zones])), 1)
        self.assertEqual(len(analyze_week.filter_activities([with_zones])), 1)

    def test_untagged_activity_above_load_threshold_is_kept(self):
        heavy = _activity(tags=[], icu_training_load=85)

        self.assertEqual(len(prepare_activities.filter_activities([heavy])), 1)
        self.assertEqual(len(analyze_week.filter_activities([heavy])), 1)

    def test_untagged_run_with_any_training_load_is_kept(self):
        light_run = _activity(type="Run", tags=[], icu_training_load=3)

        self.assertEqual(len(prepare_activities.filter_activities([light_run])), 1)
        self.assertEqual(len(analyze_week.filter_activities([light_run])), 1)

    def test_untagged_run_without_training_load_is_dropped(self):
        empty_run = _activity(type="Run", tags=[], icu_training_load=None)

        self.assertEqual(prepare_activities.filter_activities([empty_run]), [])
        self.assertEqual(analyze_week.filter_activities([empty_run]), [])

    def test_run_with_hr_zones_without_power_is_kept_without_power_fields(self):
        run = _activity(
            type="Run",
            icu_zone_times=None,
            icu_hr_zone_times=[1800, 0, 0, 0, 0, 0, 0],
            average_heartrate=142,
        )

        self.assertEqual(len(prepare_activities.filter_activities([run])), 1)
        self.assertEqual(len(analyze_week.filter_activities([run])), 1)

        exported = prepare_activities.extract_fields(
            run,
            interval_hr_analysis={
                "hr_start_avg": 140,
                "hr_end_avg": 145,
                "hr_drift_pct": 3.6,
                "hr_power_decoupling": None,
            },
        )
        self.assertEqual(exported["type"], "Run")
        self.assertEqual(exported["avg_hr"], 142)
        self.assertEqual(exported["z1_z2_pct"], 100.0)
        self.assertNotIn("hr_power_decoupling", exported["interval_hr_analysis"])
        self.assertNotIn("avg_power", exported)
        self.assertNotIn("norm_power", exported)
        self.assertNotIn("activity_ftp", exported)
        self.assertNotIn("polarization_index", exported)
        self.assertNotIn("power_curve", exported)
        self.assertNotIn("wbal_summary", exported)
        self.assertFalse(prepare_activities._needs_wbal(run, 25.0))


class ActivityDateWindowTests(unittest.TestCase):
    def test_activity_outside_lookback_window_is_dropped(self):
        old = _activity(
            icu_average_watts=210,
            start_date_local=(date.today() - timedelta(days=60)).isoformat() + "T09:00:00",
        )

        self.assertEqual(prepare_activities.filter_activities([old]), [])


if __name__ == "__main__":
    unittest.main()
