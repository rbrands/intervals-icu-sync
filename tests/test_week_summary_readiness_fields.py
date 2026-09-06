import importlib.util
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(module_name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


analyze_week = _load_module(
    "analyze_week_script",
    "scripts/analyze_week.py",
)
get_metrics = _load_module(
    "get_metrics_script",
    "scripts/get_metrics.py",
)
prepare_week_for_coach = _load_module(
    "prepare_week_for_coach_readiness_script",
    "scripts/prepare_week_for_coach.py",
)
week_data_schema = _load_module(
    "week_data_schema_model",
    "src/intervals_icu/week_data_schema.py",
)


class WeekSummaryReadinessFieldTests(unittest.TestCase):
    def test_training_readiness_caps_positive_score_after_yesterdays_hard_session(self):
        metrics = {
            "sleep_secs": 28860,
            "sleep_quality": "GOOD",
            "wellness_trends": {
                "hrv": {"current": 70.0, "avg_7d": 61.57, "trend_7d": "up"},
                "resting_hr": {"current": 40.0, "avg_7d": 41.71, "trend_7d": "down"},
            },
        }
        summary = {
            "ctl": 60.9,
            "atl": 66.7,
            "form_zone": "grey_zone",
            "form_percent_display": -9.5,
            "days_since_last_hard_session": 1,
        }

        readiness = prepare_week_for_coach.compute_training_readiness(metrics, summary)

        self.assertEqual(readiness["status"], "yellow")
        self.assertEqual(readiness["score"], 5)
        self.assertEqual(readiness["confidence"], "high")
        self.assertIn("capped at yellow", readiness["safety_vetoes"][0])

    def test_training_readiness_uses_safety_veto_for_high_risk_form(self):
        readiness = prepare_week_for_coach.compute_training_readiness(
            {},
            {"ctl": 60, "atl": 90, "form_zone": "high_risk", "days_since_last_hard_session": 3},
        )

        self.assertEqual(readiness["status"], "red")
        self.assertIn("high-risk", readiness["safety_vetoes"][0])

    def test_training_readiness_is_green_when_form_and_recency_are_positive(self):
        readiness = prepare_week_for_coach.compute_training_readiness(
            {},
            {"ctl": 60, "atl": 55, "form_zone": "fresh", "days_since_last_hard_session": 3},
        )

        self.assertEqual(readiness["status"], "green")
        self.assertEqual(readiness["score"], 4)
        self.assertEqual(readiness["confidence"], "medium")

    def test_training_readiness_is_red_after_hard_session_today(self):
        readiness = prepare_week_for_coach.compute_training_readiness(
            {},
            {"ctl": 60, "atl": 55, "form_zone": "fresh", "days_since_last_hard_session": 0},
        )

        self.assertEqual(readiness["status"], "red")
        self.assertIn("today", readiness["safety_vetoes"][0])

    def test_training_readiness_uses_safety_veto_for_two_adverse_recovery_signals(self):
        metrics = {
            "sleep_secs": 5 * 3600,
            "sleep_quality": "POOR",
            "wellness_trends": {
                "hrv": {"current": 50, "avg_7d": 60, "trend_7d": "down"},
                "resting_hr": {"current": 40, "avg_7d": 40, "trend_7d": "stable"},
            },
        }
        summary = {
            "ctl": 60,
            "atl": 55,
            "form_zone": "fresh",
            "days_since_last_hard_session": 3,
        }

        readiness = prepare_week_for_coach.compute_training_readiness(metrics, summary)

        self.assertEqual(readiness["status"], "red")
        self.assertIn("two recovery signals", readiness["safety_vetoes"][0])

    def test_training_readiness_is_unknown_without_usable_signals(self):
        readiness = prepare_week_for_coach.compute_training_readiness({}, {})

        self.assertEqual(readiness["status"], "unknown")
        self.assertEqual(readiness["score"], 0)
        self.assertEqual(readiness["confidence"], "low")
        self.assertTrue(all(signal["status"] == "unavailable" for signal in readiness["signals"]))

    def test_compute_form_returns_ctl_and_atl(self):
        form = analyze_week.compute_form(60.0, 75.0)

        self.assertEqual(form["ctl"], 60.0)
        self.assertEqual(form["atl"], 75.0)
        self.assertIn("form_pct", form)
        self.assertIn("form_zone", form)

    def test_week_data_schema_places_ctl_atl_in_week_summary(self):
        metric_fields = week_data_schema.Metrics.model_fields
        summary_fields = week_data_schema.WeekSummary.model_fields

        self.assertNotIn("ctl", metric_fields)
        self.assertNotIn("atl", metric_fields)
        self.assertIn("ctl", summary_fields)
        self.assertIn("atl", summary_fields)
        self.assertIn("training_readiness", summary_fields)
        self.assertNotIn("training_readiness", metric_fields)

    def test_main_saves_form_when_week_has_no_rides(self):
        with (
            patch.object(analyze_week, "load_data", return_value=[]),
            patch.object(analyze_week, "filter_activities", return_value=[]),
            patch.object(analyze_week, "load_training_plan", return_value=[]),
            patch.object(analyze_week, "load_metrics", return_value={"ctl": 60.0, "atl": 75.0}),
            patch.object(analyze_week, "save_json") as save_json,
            self.assertRaises(SystemExit),
        ):
            analyze_week.main()

        saved_form = save_json.call_args.args[0]
        self.assertEqual(saved_form["ctl"], 60.0)
        self.assertEqual(saved_form["atl"], 75.0)
        self.assertEqual(saved_form["form_absolute"], -15.0)
        self.assertEqual(saved_form["form_pct"], -0.25)
        self.assertEqual(saved_form["form_percent_display"], -25.0)
        self.assertEqual(saved_form["form_zone"], "optimal")

    def test_compute_ftp_eftp_delta_pct(self):
        self.assertEqual(get_metrics.compute_ftp_eftp_delta_pct(100, 110), 10.0)
        self.assertEqual(get_metrics.compute_ftp_eftp_delta_pct(260, 260.2), 0.08)

    def test_compute_days_since_last_hard_session_uses_distribution_labels(self):
        activities = [
            {
                "start_date_local": "2026-08-25T10:00:00Z",
                "icu_zone_times": [{"id": "Z1", "secs": 2000}, {"id": "Z5", "secs": 1000}],
            },
            {
                "start_date_local": "2026-08-27T10:00:00Z",
                "icu_zone_times": [{"id": "Z1", "secs": 5000}, {"id": "Z5", "secs": 2000}],
            },
            {
                "start_date_local": "2026-08-30T10:00:00Z",
                "icu_zone_times": [{"id": "Z1", "secs": 7000}, {"id": "Z3", "secs": 800}],
            },
        ]
        today = date.fromisoformat("2026-08-31")

        self.assertEqual(
            analyze_week.compute_days_since_last_distribution(activities, ["HIIT"], today),
            4,
        )
        self.assertEqual(
            analyze_week.compute_days_since_last_distribution(activities, ["HIIT", "Polarized"], today),
            4,
        )
        self.assertEqual(
            analyze_week.compute_days_since_last_distribution(activities, ["HIIT", "Polarized", "Threshold"], today),
            4,
        )

    def test_fueling_form_prioritizes_durability_limited_flag(self):
        fueling_data = {
            "weekly_summary": {
                "avg_carbs_per_hour": 55,
                "number_of_underfueled_sessions": 0,
                "number_of_long_rides": 1,
                "avg_fueling_ratio": 0.6,
            },
            "activities": [
                {"name": "Long drift ride", "carbs_per_hour": 45},
            ],
        }
        activities = [
            {
                "name": "Long drift ride",
                "type": "Ride",
                "moving_time": 2 * 3600,
                "decoupling": 9.2,
            },
        ]

        result = analyze_week.analyse_fueling_form(-0.35, fueling_data, activities)

        self.assertEqual(result["fueling_status"], "moderate")
        self.assertTrue(result["durability_limited_by_fueling"])
        self.assertEqual(result["interpretation"], "Durability appears limited by fueling")
        self.assertNotIn("adequate", result["interpretation"])

    def test_short_high_decoupling_ride_does_not_limit_durability_by_fueling(self):
        fueling_data = {
            "weekly_summary": {
                "avg_carbs_per_hour": 55,
                "number_of_underfueled_sessions": 0,
                "number_of_long_rides": 1,
                "avg_fueling_ratio": 0.6,
            },
            "activities": [
                {"name": "Short drift ride", "carbs_per_hour": 45},
            ],
        }
        activities = [
            {
                "name": "Short drift ride",
                "type": "Ride",
                "moving_time": 55 * 60,
                "decoupling": 9.2,
            },
        ]

        result = analyze_week.analyse_fueling_form(-0.35, fueling_data, activities)

        self.assertFalse(result["durability_limited_by_fueling"])
        self.assertEqual(result["interpretation"], "High training load, but fueling is adequate")


if __name__ == "__main__":
    unittest.main()
