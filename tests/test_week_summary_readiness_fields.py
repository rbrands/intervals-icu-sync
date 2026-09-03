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
week_data_schema = _load_module(
    "week_data_schema_model",
    "src/intervals_icu/week_data_schema.py",
)


class WeekSummaryReadinessFieldTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
