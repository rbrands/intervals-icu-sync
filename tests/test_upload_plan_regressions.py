import contextlib
import importlib.util
import io
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from src.intervals_icu.client import _steps_to_zwo, create_activity


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


def _load_check_plan_tss_module():
    module_path = REPO_ROOT / "scripts" / "check_plan_tss.py"
    spec = importlib.util.spec_from_file_location("check_plan_tss_script", module_path)
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

    @patch("src.intervals_icu.client.requests.post")
    def test_create_activity_sends_raw_workout_doc_unchanged(self, post):
        raw_workout_doc = {
            "steps": [
                {"duration": 300, "power": {"units": "%ftp", "value": 60}}
            ]
        }
        post.return_value.raise_for_status.return_value = None
        post.return_value.json.return_value = {"id": 123}

        create_activity(
            api_key="test-key",
            athlete_id="test-athlete",
            name="Stored workout",
            start_date_local="2026-05-19T00:00:00",
            duration=300,
            raw_workout_doc=raw_workout_doc,
        )

        payload = json.loads(post.call_args.kwargs["data"].decode("utf-8"))
        self.assertEqual(payload["workout_doc"], raw_workout_doc)
        self.assertNotIn("file_contents_base64", payload)
        self.assertNotIn("filename", payload)

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

    def test_upload_plan_uses_library_workout_content(self):
        module = _load_upload_plan_module()
        captured: dict = {}
        library_workout = {
            "id": 81,
            "name": "Stored VO2Max",
            "type": "Ride",
            "moving_time": 3600,
            "description": "Stored execution notes",
            "tags": ["vo2max-moderate"],
            "workout_doc": {
                "steps": [
                    {"duration": 300, "power": {"units": "%ftp", "value": 60}}
                ]
            },
        }

        module.get_events = lambda *args, **kwargs: []
        module.get_library_workout = lambda *args, **kwargs: library_workout

        def _fake_create_activity(**kwargs):
            captured.update(kwargs)
            return {"id": "evt-1"}

        module.create_activity = _fake_create_activity

        plan = [
            {
                "date": "2026-05-19",
                "name": "Generated placeholder",
                "duration_minutes": 30,
                "library_workout_id": 81,
                "tags": ["recovery-low"],
                "steps": [{"duration_seconds": 1800, "power_pct_ftp": 50}],
                "fueling": {"carbs_per_hour": 90, "total_carbs": 90},
            }
        ]

        with contextlib.redirect_stdout(io.StringIO()):
            module.upload_plan(plan, dry_run=False)

        self.assertEqual(captured["name"], "Stored VO2Max")
        self.assertEqual(captured["duration"], 3600)
        self.assertEqual(captured["description"], "Stored execution notes")
        self.assertEqual(captured["tags"], ["vo2max-moderate"])
        self.assertEqual(captured["raw_workout_doc"], library_workout["workout_doc"])

    def test_upload_plan_preserves_library_workout_tss_without_steps(self):
        module = _load_upload_plan_module()
        captured: dict = {}
        library_workout = {
            "id": 81,
            "name": "Stored Recovery",
            "type": "Ride",
            "moving_time": 2700,
            "description": "Stored execution notes",
            "icu_training_load": 70,
            "tags": ["recovery-low"],
        }

        module.get_events = lambda *args, **kwargs: []
        module.get_library_workout = lambda *args, **kwargs: library_workout

        def _fake_create_activity(**kwargs):
            captured.update(kwargs)
            return {"id": "evt-1"}

        module.create_activity = _fake_create_activity

        plan = [
            {
                "date": "2026-05-19",
                "name": "Generated placeholder",
                "duration_minutes": 45,
                "library_workout_id": 81,
            }
        ]

        with contextlib.redirect_stdout(io.StringIO()):
            module.upload_plan(plan, dry_run=False)

        self.assertEqual(captured["training_load"], 70)
        self.assertIsNone(captured["raw_workout_doc"])


class CheckPlanTssRegressionTests(unittest.TestCase):
    def test_evaluate_plan_detects_mismatch_and_target_deviation(self):
        module = _load_check_plan_tss_module()
        plan = [
            {
                "date": "2026-05-18",
                "tss": 120,
                "steps": [
                    {"duration_seconds": 1800, "power_pct_ftp": 100},
                    {"duration_seconds": 1800, "power_pct_ftp": 50},
                ],
            },
            {
                "date": "2026-05-20",
                "tss": 30,
                "library_workout_id": 77,
            },
        ]

        result = module.evaluate_plan(plan, load_target=200, tolerance_pct=10)

        self.assertEqual(result["week"]["total_tss"], 92)
        self.assertFalse(result["week"]["within_tolerance"])
        self.assertFalse(result["valid"])
        self.assertTrue(any("Workout on 2026-05-18" in issue for issue in result["issues"]))
        self.assertTrue(any("Weekly total 92 TSS" in issue for issue in result["issues"]))


if __name__ == "__main__":
    unittest.main()
