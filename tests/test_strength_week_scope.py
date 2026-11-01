import importlib.util
import unittest
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(module_name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


analyze_week = _load_module("analyze_week_strength_scope_script", "scripts/analyze_week.py")
fueling_analysis = _load_module(
    "fueling_analysis_strength_scope_script", "scripts/fueling_analysis.py"
)
prepare_week = _load_module(
    "prepare_week_strength_scope_script", "scripts/prepare_week_for_coach.py"
)
week_data_schema = _load_module(
    "week_data_schema_strength_scope", "src/intervals_icu/week_data_schema.py"
)


def _raw_activity(activity_type: str, load: int, moving_time: int, **overrides) -> dict:
    activity = {
        "id": activity_type,
        "type": activity_type,
        "source": "GARMIN",
        "start_date_local": date.today().isoformat() + "T09:00:00",
        "icu_training_load": load,
        "moving_time": moving_time,
        "tags": [],
    }
    activity.update(overrides)
    return activity


class StrengthFuelingScopeTests(unittest.TestCase):
    def test_strength_is_excluded_from_fueling_analysis_and_weekly_averages(self):
        ride = {
            "type": "Ride",
            "date": date.today().isoformat(),
            "name": "Long ride",
            "duration_hours": 3,
            "carbs_ingested_g": 30,
            "carbs_used_g": 100,
            "decoupling": 11,
            "rpe": 8,
            "tags": [],
        }
        strength = {
            "type": "WeightTraining",
            "date": date.today().isoformat(),
            "name": "Strength",
            "duration_hours": 2,
            "carbs_ingested_g": 200,
            "carbs_used_g": 200,
            "tags": ["strength-maximum"],
        }
        ride_only = fueling_analysis._filter_by_lookback([ride])
        ride_and_strength = fueling_analysis._filter_by_lookback([ride, strength])
        ride_summary = fueling_analysis.summarize_week(
            [fueling_analysis.analyze_activity(activity) for activity in ride_only]
        )
        combined_summary = fueling_analysis.summarize_week(
            [fueling_analysis.analyze_activity(activity) for activity in ride_and_strength]
        )

        self.assertEqual(len(ride_and_strength), 1)
        self.assertEqual(combined_summary, ride_summary)
        self.assertIsNone(fueling_analysis.classify_ride(strength))
        self.assertIsNone(
            fueling_analysis.classify_ride(
                {"type": "Ride", "tags": ["strength-maintenance"]}
            )
        )

    def test_strength_does_not_change_fueling_form_analysis(self):
        fueling_data = {
            "weekly_summary": {
                "avg_carbs_per_hour": 55,
                "number_of_underfueled_sessions": 0,
                "number_of_long_rides": 1,
                "avg_fueling_ratio": 0.6,
            },
            "activities": [{"name": "Long ride", "carbs_per_hour": 45}],
        }
        ride = {
            "name": "Long ride",
            "type": "Ride",
            "moving_time": 3 * 3600,
            "training_distribution": "Base",
            "decoupling": 9.2,
        }
        strength = {
            "name": "Strength",
            "type": "WeightTraining",
            "moving_time": 3 * 3600,
            "training_distribution": "Base",
            "decoupling": 12,
            "tags": ["strength-maximum"],
        }

        ride_result = analyze_week.analyse_fueling_form(-0.35, fueling_data, [ride])
        combined_result = analyze_week.analyse_fueling_form(
            -0.35, fueling_data, [ride, strength]
        )

        self.assertEqual(combined_result, ride_result)

    def test_consolidation_does_not_attach_fueling_to_strength(self):
        activities = [
            {"type": "WeightTraining", "date": "2026-11-01", "name": "Strength"},
            {"type": "Ride", "date": "2026-11-01", "name": "Ride"},
        ]
        fueling = {
            "activities": [
                {
                    "date": "2026-11-01",
                    "name": "Ride",
                    "fueling_status": "fueling required",
                }
            ],
            "weekly_summary": {"avg_carbs_per_hour": 60},
        }

        merged, cleaned = prepare_week._merge_fueling_into_activities(activities, fueling)

        self.assertNotIn("fueling", merged[0])
        self.assertEqual(merged[1]["fueling"], {"fueling_status": "fueling required"})
        self.assertNotIn("activities", cleaned)


class StrengthWeekSummaryTests(unittest.TestCase):
    def test_sample_strength_activity_does_not_change_ride_run_totals(self):
        rides = [
            _raw_activity("Ride", 100, 3600),
            _raw_activity("VirtualRide", 80, 7200),
            _raw_activity("MountainBikeRide", 55, 5400),
            _raw_activity("GravelRide", 50, 1800),
        ]
        strength = _raw_activity(
            "WeightTraining",
            9,
            3600,
            tags=["strength-maximum"],
            decoupling=12,
            icu_zone_times=[{"id": "Z5", "secs": 3600}],
        )

        without_strength = analyze_week.compute_metrics(rides)
        with_strength = analyze_week.compute_metrics(rides + [strength])

        self.assertEqual(analyze_week.filter_activities([strength]), [strength])
        self.assertEqual(with_strength["total_training_load"], 285)
        self.assertEqual(with_strength["total_training_load"], without_strength["total_training_load"])
        self.assertEqual(with_strength["number_of_activities"], 4)
        self.assertEqual(with_strength["total_time_hours"], without_strength["total_time_hours"])
        self.assertEqual(with_strength["longest_activity_hours"], without_strength["longest_activity_hours"])
        self.assertEqual(with_strength["ride_load"], 285)
        self.assertEqual(with_strength["strength_load"], 9)
        self.assertEqual(with_strength["strength_sessions"], 1)
        self.assertEqual(with_strength["strength_time_hours"], 1)
        self.assertEqual(with_strength["ride_sessions"], 4)
        self.assertEqual(with_strength["ride_time_hours"], 5)
        self.assertEqual(with_strength["vo2_sessions"], without_strength["vo2_sessions"])
        self.assertEqual(with_strength["threshold_sessions"], without_strength["threshold_sessions"])
        self.assertEqual(with_strength["endurance_sessions"], without_strength["endurance_sessions"])
        self.assertEqual(with_strength["avg_decoupling"], without_strength["avg_decoupling"])
        self.assertEqual(
            with_strength["high_decoupling_rides"],
            without_strength["high_decoupling_rides"],
        )
        self.assertEqual(
            with_strength["days_since_last_hiit"],
            without_strength["days_since_last_hiit"],
        )
        self.assertEqual(
            with_strength["days_since_last_polarized"],
            without_strength["days_since_last_polarized"],
        )
        self.assertEqual(
            with_strength["days_since_last_hard_session"],
            without_strength["days_since_last_hard_session"],
        )
        self.assertIsNone(
            analyze_week.compute_aerobic_threshold_estimate(
                [
                    {
                        "type": "WeightTraining",
                        "dfa_a1_summary": {
                            "valid": True,
                            "power_at_0_75": 200,
                            "hr_at_0_75": 140,
                            "threshold_windows": 4,
                        },
                    }
                ],
                250,
                [55, 75, 90],
            )
        )

    def test_run_remains_in_combined_totals_and_has_separate_totals(self):
        ride = _raw_activity("Ride", 100, 3600)
        run = _raw_activity("Run", 20, 1800)
        strength = _raw_activity("WeightTraining", 9, 900)

        summary = analyze_week.compute_metrics([ride, run, strength])

        self.assertEqual(summary["total_training_load"], 120)
        self.assertEqual(summary["number_of_activities"], 2)
        self.assertEqual(summary["total_time_hours"], 1.5)
        self.assertEqual(summary["run_load"], 20)
        self.assertEqual(summary["run_sessions"], 1)
        self.assertEqual(summary["run_time_hours"], 0.5)

    def test_week_summary_schema_accepts_per_sport_totals(self):
        fields = week_data_schema.WeekSummary.model_fields

        self.assertTrue(
            {
                "ride_load",
                "run_load",
                "strength_load",
                "ride_sessions",
                "run_sessions",
                "strength_sessions",
                "ride_time_hours",
                "run_time_hours",
                "strength_time_hours",
            }.issubset(fields)
        )


if __name__ == "__main__":
    unittest.main()
