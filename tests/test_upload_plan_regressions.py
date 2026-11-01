import base64
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

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
    def test_validate_plan_does_not_include_plan_path_for_schema_errors(self):
        plan_path = REPO_ROOT / "tests" / "invalid-temporary-plan.json"
        schema_path = REPO_ROOT / "contracts" / "week-plan" / "week-plan.schema.json"
        plan_path.write_text(
            json.dumps({"workouts": [{"date": "2026-05-19", "name": "Bad type", "duration_minutes": 30, "activity_type": "Jogging"}]}),
            encoding="utf-8",
        )
        self.addCleanup(plan_path.unlink, missing_ok=True)

        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "validate_plan.py"),
                "--plan",
                str(plan_path),
                "--schema",
                str(schema_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("validation error(s) in plan", result.stdout)
        self.assertNotIn(str(plan_path), result.stdout)

    def test_validate_plan_does_not_echo_entire_plan_for_root_schema_errors(self):
        plan_path = REPO_ROOT / "tests" / "invalid-root-plan.json"
        schema_path = REPO_ROOT / "contracts" / "week-plan" / "week-plan.schema.json"
        plan = {"unexpected": "value", "payload": ["should not be echoed"]}
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        self.addCleanup(plan_path.unlink, missing_ok=True)

        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "validate_plan.py"),
                "--plan",
                str(plan_path),
                "--schema",
                str(schema_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required property 'workouts'", result.stdout)
        self.assertNotIn(json.dumps(plan), result.stdout)

    def test_validate_plan_reports_missing_nested_required_property_without_echoing_plan(self):
        plan_path = REPO_ROOT / "tests" / "missing-date-plan.json"
        schema_path = REPO_ROOT / "contracts" / "week-plan" / "week-plan.schema.json"
        plan = {"workouts": [{"name": "Workout without date", "duration_minutes": 45}]}
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        self.addCleanup(plan_path.unlink, missing_ok=True)

        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "validate_plan.py"),
                "--plan",
                str(plan_path),
                "--schema",
                str(schema_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("$.workouts[0]: missing required property 'date'", result.stdout)
        self.assertNotIn(json.dumps(plan), result.stdout)

    def test_week_plan_schema_accepts_valid_activity_types(self):
        schema = json.loads(
            (REPO_ROOT / "contracts" / "week-plan" / "week-plan.schema.json").read_text(
                encoding="utf-8"
            )
        )
        validator = Draft202012Validator(schema)
        plan = {
            "workouts": [
                {
                    "date": "2026-05-19",
                    "name": "Easy run",
                    "duration_minutes": 30,
                    "activity_type": "Run",
                },
                {
                    "date": "2026-05-20",
                    "name": "Strength",
                    "duration_minutes": 45,
                    "activity_type": "WeightTraining",
                    "tags": ["strength-adaptation"],
                },
                {
                    "date": "2026-05-21",
                    "name": "Default ride",
                    "duration_minutes": 60,
                },
            ]
        }

        self.assertEqual(list(validator.iter_errors(plan)), [])

    def test_week_plan_schema_rejects_invalid_activity_type(self):
        schema = json.loads(
            (REPO_ROOT / "contracts" / "week-plan" / "week-plan.schema.json").read_text(
                encoding="utf-8"
            )
        )
        plan = {
            "workouts": [
                {
                    "date": "2026-05-19",
                    "name": "Bad type",
                    "duration_minutes": 30,
                    "activity_type": "Jogging",
                }
            ]
        }

        errors = list(Draft202012Validator(schema).iter_errors(plan))
        self.assertTrue(errors)

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

    @patch("src.intervals_icu.client.requests.post")
    def test_create_activity_defaults_activity_type_to_ride(self, post):
        post.return_value.raise_for_status.return_value = None
        post.return_value.json.return_value = {"id": 123}

        create_activity(
            api_key="test-key",
            athlete_id="test-athlete",
            name="Default ride",
            start_date_local="2026-05-19T00:00:00",
            duration=300,
        )

        payload = json.loads(post.call_args.kwargs["data"].decode("utf-8"))
        self.assertEqual(payload["type"], "Ride")

    @patch("src.intervals_icu.client.requests.post")
    def test_create_activity_respects_custom_activity_type(self, post):
        post.return_value.raise_for_status.return_value = None
        post.return_value.json.return_value = {"id": 123}

        create_activity(
            api_key="test-key",
            athlete_id="test-athlete",
            name="Easy run",
            start_date_local="2026-05-19T00:00:00",
            duration=1800,
            activity_type="Run",
        )

        payload = json.loads(post.call_args.kwargs["data"].decode("utf-8"))
        self.assertEqual(payload["type"], "Run")

    def test_create_activity_rejects_invalid_activity_type(self):
        with self.assertRaises(ValueError):
            create_activity(
                api_key="test-key",
                athlete_id="test-athlete",
                name="Bad type",
                start_date_local="2026-05-19T00:00:00",
                duration=1800,
                activity_type="Jogging",
            )

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

    def test_upload_plan_dry_run_shows_custom_activity_type_without_steps(self):
        module = _load_upload_plan_module()
        plan = [
            {
                "date": "2026-05-19",
                "name": "Easy run",
                "duration_minutes": 30,
                "activity_type": "Run",
            },
            {
                "date": "2026-05-20",
                "name": "Strength",
                "duration_minutes": 45,
                "activity_type": "WeightTraining",
            },
        ]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            module.upload_plan(plan, dry_run=True)
        text = output.getvalue()
        self.assertIn("Easy run", text)
        self.assertIn("Run, 30 min", text)
        self.assertIn("Strength", text)
        self.assertIn("WeightTraining, 45 min", text)

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

    def test_upload_plan_truncates_name_but_preserves_description(self):
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
        self.assertEqual(captured["description"], "D" * 800)

    def test_upload_plan_preserves_complete_microburst_description_on_create_and_update(self):
        description = (
            "Race-specific session for repeated accelerations out of corners, attacks, "
            "and incomplete recovery. Keep the hard efforts explosive but technically "
            "controlled, with easy running power between them. TSS: 71. Fueling: take "
            "60\u201390 g carbohydrate per hour and drink consistently before the harder repetitions."
        )
        steps = [
            {"duration_seconds": 900, "power_pct_ftp": 50},
            {"duration_seconds": 600, "power_pct_ftp": 70},
        ]
        for block, repetitions in enumerate((8, 8, 8)):
            if block:
                steps.append({"duration_seconds": 300, "power_pct_ftp": 55})
            for _ in range(repetitions):
                steps.extend([
                    {"duration_seconds": 30, "power_pct_ftp": 140},
                    {"duration_seconds": 30, "power_pct_ftp": 55},
                ])
        steps.append({"duration_seconds": 900, "power_pct_ftp": 50})
        self.assertEqual(len(steps), 53)
        self.assertEqual(sum(step["duration_seconds"] for step in steps), 74 * 60)

        plan = [{
            "date": "2026-10-16",
            "name": "Criterium Microburst Session",
            "duration_minutes": 74,
            "description": description,
            "steps": steps,
        }]

        for existing in (False, True):
            with self.subTest(existing=existing):
                module = _load_upload_plan_module()
                events = [{
                    "id": 123,
                    "name": plan[0]["name"],
                    "start_date_local": "2026-10-16T00:00:00",
                }] if existing else []
                with (
                    patch.object(module, "get_events", return_value=events),
                    patch.object(module, "create_activity", return_value={"id": 123}) as create,
                    patch.object(module, "update_event", return_value={"id": 123}) as update,
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    module.upload_plan(plan)

                if existing:
                    create.assert_not_called()
                    update.assert_called_once()
                    payload = update.call_args.args[3]
                else:
                    update.assert_not_called()
                    create.assert_called_once()
                    payload = create.call_args.kwargs
                self.assertEqual(payload["description"], description)
                if existing:
                    zwo = base64.b64decode(payload["file_contents_base64"]).decode()
                    self.assertEqual(zwo.count("<SteadyState "), len(steps))
                else:
                    self.assertEqual(payload["duration"], 74 * 60)
                    self.assertEqual(payload["workout"], {"steps": steps})

    def test_upload_plan_preserves_long_description_with_appended_fueling(self):
        module = _load_upload_plan_module()
        description = "Coaching notes. " * 50
        plan = [{
            "date": "2026-10-16",
            "name": "Endurance ride",
            "duration_minutes": 60,
            "description": description,
            "fueling": {"carbs_per_hour": 60, "total_carbs": 60},
        }]
        with (
            patch.object(module, "get_events", return_value=[]),
            patch.object(module, "create_activity", return_value={"id": 123}) as create,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            module.upload_plan(plan)
        self.assertEqual(
            create.call_args.kwargs["description"],
            description + "\nFueling: 60g carbs/h, 60g total",
        )

    def test_upload_plan_uses_library_workout_content(self):
        module = _load_upload_plan_module()
        captured: dict = {}
        library_workout = {
            "id": 81,
            "name": "Stored VO2Max",
            "type": "Ride",
            "moving_time": 3600,
            "description": "Stored execution notes. " * 50,
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
        self.assertEqual(captured["description"], library_workout["description"])
        self.assertEqual(captured["tags"], ["vo2max-moderate"])
        self.assertEqual(captured["raw_workout_doc"], library_workout["workout_doc"])
        self.assertEqual(captured["activity_type"], "Ride")

    def test_upload_plan_library_workout_type_takes_precedence(self):
        module = _load_upload_plan_module()
        captured: dict = {}
        library_workout = {
            "id": 81,
            "name": "Stored Strength",
            "type": "WeightTraining",
            "moving_time": 2700,
            "description": "Stored execution notes",
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
                "activity_type": "Run",
            }
        ]

        with contextlib.redirect_stdout(io.StringIO()):
            module.upload_plan(plan, dry_run=False)

        self.assertEqual(captured["activity_type"], "WeightTraining")

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

    def test_upload_plan_passes_custom_activity_type_without_steps(self):
        module = _load_upload_plan_module()
        captured: dict = {}

        module.get_events = lambda *args, **kwargs: []

        def _fake_create_activity(**kwargs):
            captured.update(kwargs)
            return {"id": "evt-1"}

        module.create_activity = _fake_create_activity

        plan = [
            {
                "date": "2026-05-19",
                "name": "Easy run",
                "duration_minutes": 30,
                "activity_type": "Run",
            }
        ]

        with contextlib.redirect_stdout(io.StringIO()):
            module.upload_plan(plan, dry_run=False)

        self.assertEqual(captured["activity_type"], "Run")
        self.assertIsNone(captured["workout"])
        self.assertIsNone(captured["raw_workout_doc"])

    def test_upload_plan_update_event_includes_custom_activity_type(self):
        module = _load_upload_plan_module()
        captured: dict = {}

        module.get_events = lambda *args, **kwargs: [
            {"id": 123, "name": "Easy run", "start_date_local": "2026-05-19T00:00:00"}
        ]

        def _fake_update_event(api_key, athlete_id, event_id, payload):
            captured["event_id"] = event_id
            captured["payload"] = payload
            return {"id": event_id}

        module.update_event = _fake_update_event

        plan = [
            {
                "date": "2026-05-19",
                "name": "Easy run",
                "duration_minutes": 30,
                "activity_type": "Run",
            }
        ]

        with contextlib.redirect_stdout(io.StringIO()):
            module.upload_plan(plan, dry_run=False)

        self.assertEqual(captured["event_id"], 123)
        self.assertEqual(captured["payload"]["type"], "Run")

    def test_upload_plan_rejects_invalid_activity_type(self):
        module = _load_upload_plan_module()

        module.get_events = lambda *args, **kwargs: []

        plan = [
            {
                "date": "2026-05-19",
                "name": "Bad type",
                "duration_minutes": 30,
                "activity_type": "Jogging",
            }
        ]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            module.upload_plan(plan, dry_run=False)

        self.assertIn("Invalid activity_type", output.getvalue())
        self.assertIn("0 uploaded, 0 skipped, 1 failed", output.getvalue())


class CheckPlanTssRegressionTests(unittest.TestCase):
    def test_only_ride_entries_count_toward_weekly_target(self):
        module = _load_check_plan_tss_module()
        plan = [
            {"date": "2026-11-02", "tss": 100},
            {"date": "2026-11-03", "tss": 80, "activity_type": None},
            {"date": "2026-11-04", "tss": 60, "activity_type": "VirtualRide"},
            {"date": "2026-11-04", "tss": 15, "activity_type": "WeightTraining"},
            {"date": "2026-11-05", "tss": 30, "activity_type": "Run",
             "steps": [{"duration_seconds": 3600, "power_pct_ftp": 100}]},
        ]
        result = module.evaluate_plan(plan, load_target=240)
        self.assertEqual(result["week"]["planned_tss"], 240)
        self.assertEqual(result["week"]["planned_ride_tss"], 240)
        self.assertEqual(result["week"]["planned_other_tss"], 45)
        self.assertEqual(result["week"]["total_tss"], 240)
        self.assertTrue(result["week"]["within_tolerance"])
        self.assertTrue(result["valid"])
        self.assertEqual([row["counted"] for row in result["workouts"]], [True, True, True, False, False])
        for row in result["workouts"][3:]:
            self.assertEqual(row["computed_tss"], row["stated_tss"])
            self.assertFalse(row["mismatch"])

    def test_current_week_checks_completed_and_planned_tss_against_full_target(self):
        module = _load_check_plan_tss_module()
        plan = [
            {
                "date": "2026-10-18",
                "tss": 160,
                "library_workout_id": 77,
            },
        ]

        result = module.evaluate_plan(
            plan,
            load_target=400,
            completed_tss=200,
            tolerance_pct=10,
        )

        self.assertEqual(result["week"]["completed_tss"], 200)
        self.assertEqual(result["week"]["planned_tss"], 160)
        self.assertEqual(result["week"]["total_tss"], 360)
        self.assertTrue(result["week"]["within_tolerance"])

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


class StrengthPlanValidationTests(unittest.TestCase):
    def test_time_budgets_split_weekly_rides_but_include_all_sports_on_limited_days(self):
        ride = {"date": "2026-11-02T08:00:00", "name": "Ride", "duration_minutes": 60}
        workouts = [ride, self.strength(date="2026-11-02T18:00:00")]
        for limit, status in ((1.75, "valid"), (1.5, "invalid"), (1.0, "invalid")):
            with self.subTest(limit=limit):
                data = {"week_summary": {"training_plan": [{
                    "week": "2026-11-02",
                    "weekly_time_target_hours": 1,
                    "day_constraints": [{
                        "date": "2026-11-02", "type": "LIMITED",
                        "training_allowed": True, "max_training_time_hours": limit,
                    }],
                }]}}
                result = self.validate(workouts, data)
                self.assertEqual(result["status"], status)
                self.assertEqual(result["week"]["planned_ride_hours"], 1)
                self.assertEqual(result["week"]["planned_other_hours"], 0.75)
                self.assertNotIn("exceeding weekly_time_target_hours", result["details"])
                if status == "invalid":
                    self.assertIn("LIMITED-day budget", result["details"])
        self.assertEqual(self.validate(workouts)["status"], "valid")

    def test_weekly_ride_time_cap_is_week_scoped_and_defaults_to_ride(self):
        workouts = [
            {"date": "2026-11-02", "name": "Ride", "duration_minutes": 60, "activity_type": None},
            self.strength(),
            {"date": "2026-11-09", "name": "Next week", "duration_minutes": 120},
        ]
        for target, status in ((1, "valid"), (0.5, "invalid")):
            data = {"week_summary": {"training_plan": [{
                "week": "2026-11-02", "weekly_time_target_hours": target,
            }]}}
            result = self.validate(workouts, data)
            self.assertEqual(result["status"], status)
            if status == "invalid":
                self.assertIn("planned Ride duration for week 2026-11-02 is 1 hours", result["details"])

    def test_tss_tool_reports_time_split_and_checks_optional_ride_time_cap(self):
        workouts = [
            {"date": "2026-11-02", "duration_minutes": 60},
            self.strength(),
            {"date": "2026-11-03", "duration_minutes": 30, "activity_type": "Run"},
        ]
        for target, valid in ((None, True), (1, True), (0.5, False)):
            result = json.loads(self.server.check_plan_tss(
                json.dumps(workouts), 0, weekly_time_target_hours=target,
            ))
            self.assertEqual(result["week"]["planned_ride_hours"], 1)
            self.assertEqual(result["week"]["planned_other_hours"], 1.25)
            self.assertEqual(result["week"]["time_within_budget"], valid)
            self.assertEqual(result["valid"], valid)

    @classmethod
    def setUpClass(cls):
        with patch.dict(os.environ, {"INTERVALS_API_KEY": "test-key", "ATHLETE_ID": "test-athlete"}):
            spec = importlib.util.spec_from_file_location("strength_plan_local_mcp", REPO_ROOT / "scripts" / "mcp_server.py")
            cls.server = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.server)
        from validate_plan import _expand_schema_errors, _message_for_error, _path_for_error
        cls.expand = staticmethod(_expand_schema_errors)
        cls.message = staticmethod(_message_for_error)
        cls.location = staticmethod(_path_for_error)
        schema = json.loads((REPO_ROOT / "contracts" / "week-plan" / "week-plan.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        cls.validator = Draft202012Validator(schema)

    def strength(self, **overrides):
        entry = {
            "date": "2026-11-02", "name": "Strength", "duration_minutes": 45,
            "activity_type": "WeightTraining", "tags": ["strength-adaptation"],
        }
        entry.update(overrides)
        return entry

    def validate(self, workouts, athlete_data=None):
        return json.loads(self.server.validate_week_plan(
            json.dumps({"workouts": workouts}),
            athlete_data=json.dumps(athlete_data) if athlete_data is not None else "",
        ))

    def test_strength_schema_accepts_valid_entries_and_legacy_tag(self):
        for duration in (30, 45, 75):
            for tag in ("strength-adaptation", "strength-transition", "strength-maximum", "strength-maintenance"):
                for wrapper in (True, False):
                    with self.subTest(duration=duration, tag=tag, wrapper=wrapper):
                        entries = [self.strength(duration_minutes=duration, tags=[tag, "gym"], tag="legacy", steps=[])]
                        plan = {"workouts": entries} if wrapper else entries
                        self.assertEqual(list(self.validator.iter_errors(plan)), [])

    def test_strength_schema_errors_are_located_and_readable(self):
        invalid = [
            ({"tags": []}, ".tags", "canonical strength phase tag"),
            ({"tags": ["strength-adaptation", "strength-maximum"]}, ".tags", "exactly one"),
            ({"tags": ["vo2max-high"]}, ".tags", "canonical strength phase tag"),
            ({"steps": [{"duration_seconds": 300}]}, ".steps", "absent or empty"),
            ({"workout": {"steps": [{"duration_seconds": 300}]}}, ".workout.steps", "absent or empty"),
            ({"duration_minutes": 20}, ".duration_minutes", "at least 30"),
            ({"duration_minutes": 90}, ".duration_minutes", "at most 75"),
            ({"library_workout_id": 7}, "", "library_workout_id is not allowed"),
        ]
        missing = self.strength()
        del missing["tags"]
        cases = [(self.strength(**fields), field, text) for fields, field, text in invalid]
        cases.append((missing, "", "missing required property 'tags'"))
        for entry, field, text in cases:
            with self.subTest(entry=entry):
                errors = self.expand(list(self.validator.iter_errors({"workouts": [entry]})))
                self.assertTrue(any(
                    self.location(list(error.absolute_path)).startswith("$.workouts[0]" + field)
                    and text in self.message(error)
                    for error in errors
                ))

    def test_ride_and_strength_same_day_pass_but_duplicates_fail(self):
        ride = {"date": "2026-11-02T08:00:00", "name": "Ride", "duration_minutes": 60}
        self.assertEqual(self.validate([ride, self.strength()])["status"], "valid")
        for entries in (
            [ride, dict(ride, activity_type="VirtualRide", date="2026-11-02T18:00:00")],
            [self.strength(), self.strength(date="2026-11-02T18:00:00")],
        ):
            result = self.validate(entries)
            self.assertEqual(result["status"], "invalid")
            self.assertIn("$.workouts[1].date", result["details"])
            self.assertIn("at most one", result["details"])

    def test_constraints_reject_every_sport_but_are_optional(self):
        data = {"week_summary": {"training_plan": [{
            "day_constraints": [{"date": "2026-11-02", "training_allowed": False}],
        }]}}
        for entry in (self.strength(), self.strength(activity_type="Ride"), self.strength(activity_type="Run")):
            with self.subTest(activity_type=entry["activity_type"]):
                result = self.validate([entry], data)
                self.assertEqual(result["status"], "invalid")
                self.assertIn("$.workouts[0].date: training is not allowed", result["details"])
                self.assertEqual(self.validate([entry])["status"], "valid")

    def test_mcp_strength_schema_error_uses_existing_error_format(self):
        result = self.validate([self.strength(duration_minutes=20)])
        self.assertEqual(result["status"], "invalid")
        self.assertIn("$.workouts[0].duration_minutes: must be at least 30", result["details"])

    def test_mcp_completed_tss_uses_ride_load_and_legacy_fallback_only_if_absent(self):
        for summary, expected in (
            ({"ride_load": 100, "total_training_load": 130}, 100),
            ({"total_training_load": 130}, 130),
            ({"ride_load": 0, "total_training_load": 130}, 0),
            ({"ride_load": None, "total_training_load": 130}, 0),
        ):
            with self.subTest(summary=summary):
                result = json.loads(self.server.check_plan_tss(
                    json.dumps([{"date": "2026-11-02", "tss": 20}]), 150,
                    athlete_data=json.dumps({"week_summary": summary}),
                ))
                self.assertEqual(result["week"]["completed_tss"], expected)
        tool = self.server.mcp._tool_manager.get_tool("check_plan_tss")
        self.assertIsNotNone(tool)


if __name__ == "__main__":
    unittest.main()
