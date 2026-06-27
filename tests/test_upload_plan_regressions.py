import contextlib
import importlib.util
import io
import os
import unittest
from pathlib import Path

from src.intervals_icu.client import _steps_to_zwo


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_upload_plan_module():
    os.environ.setdefault("INTERVALS_API_KEY", "test-key")
    os.environ.setdefault("ATHLETE_ID", "test-athlete")
    module_path = REPO_ROOT / "scripts" / "upload_plan.py"
    spec = importlib.util.spec_from_file_location("upload_plan_script", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class UploadPlanRegressionTests(unittest.TestCase):
    def test_steps_to_zwo_accepts_seconds_and_percent_fields(self):
        zwo = _steps_to_zwo(
            "Test",
            "",
            [
                {"duration_seconds": 300, "power_pct_ftp": 60},
                {"duration_seconds": 120, "power_pct_ftp": 95},
            ],
        )
        self.assertIn('Duration="300"', zwo)
        self.assertIn('Power="0.6"', zwo)
        self.assertIn('Duration="120"', zwo)
        self.assertIn('Power="0.95"', zwo)

    def test_upload_plan_dry_run_supports_top_level_steps(self):
        module = _load_upload_plan_module()
        plan = [
            {
                "date": "2026-05-19",
                "name": "Top-level steps",
                "duration_minutes": 60,
                "steps": [{"duration_seconds": 300, "power_pct_ftp": 60}],
            }
        ]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            module.upload_plan(plan, dry_run=True)
        self.assertIn("1 steps", output.getvalue())

    def test_upload_plan_dry_run_supports_nested_workout_steps(self):
        module = _load_upload_plan_module()
        plan = [
            {
                "date": "2026-05-19",
                "name": "Nested steps",
                "duration_minutes": 60,
                "workout": {"steps": [{"duration_seconds": 300, "power_pct_ftp": 60}]},
            }
        ]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            module.upload_plan(plan, dry_run=True)
        self.assertIn("1 steps", output.getvalue())

    def test_upload_plan_truncates_name_and_description(self):
        module = _load_upload_plan_module()
        captured: dict[str, str] = {}

        def _fake_get_events(*args, **kwargs):
            return []

        def _fake_create_activity(*, name: str, description: str, **kwargs):
            captured["name"] = name
            captured["description"] = description
            return {"id": "evt-1"}

        module.get_events = _fake_get_events
        module.create_activity = _fake_create_activity

        plan = [
            {
                "date": "2026-05-19",
                "name": "N" * 160,
                "duration_minutes": 60,
                "description": "D" * 800,
            }
        ]

        with contextlib.redirect_stdout(io.StringIO()):
            module.upload_plan(plan, dry_run=False)

        self.assertEqual(len(captured["name"]), 127)
        self.assertEqual(captured["name"], "N" * 127)
        self.assertEqual(len(captured["description"]), 512)
        self.assertEqual(captured["description"], "D" * 512)


if __name__ == "__main__":
    unittest.main()
