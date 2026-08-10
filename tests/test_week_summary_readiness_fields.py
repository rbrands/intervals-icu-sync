import importlib.util
import unittest
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


if __name__ == "__main__":
    unittest.main()
