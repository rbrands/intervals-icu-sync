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


if __name__ == "__main__":
    unittest.main()
