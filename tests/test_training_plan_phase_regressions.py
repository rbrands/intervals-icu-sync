import importlib.util
import os
import sys
import tempfile
import types
import unittest
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

os.environ.setdefault("INTERVALS_API_KEY", "test-key")
os.environ.setdefault("ATHLETE_ID", "test-athlete")

if "dotenv" not in sys.modules:
    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda *args, **kwargs: None
    sys.modules["dotenv"] = dotenv_stub


def _load_module(module_name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


prepare_week_for_coach = _load_module(
    "prepare_week_for_coach_script",
    "scripts/prepare_week_for_coach.py",
)
analyze_week = _load_module(
    "analyze_week_script",
    "scripts/analyze_week.py",
)
get_training_plan = _load_module(
    "get_training_plan_script",
    "scripts/get_training_plan.py",
)


class TrainingPlanPhaseRegressionTests(unittest.TestCase):
    def test_weekly_target_prefers_tss_and_shows_time_as_cap(self):
        entry = {
            "weekly_load_target": 300,
            "weekly_time_target_hours": 8.0,
        }

        self.assertEqual(analyze_week._format_weekly_target(entry), "300 TSS, capped at 8.0 h")

    def test_weekly_load_targets_include_time_target_when_tss_is_missing(self):
        events = [
            {
                "category": "TARGET",
                "type": "Ride",
                "start_date_local": "2026-07-20T00:00:00",
                "load_target": None,
                "time_target": 28800,
            }
        ]

        targets = get_training_plan.find_weekly_load_targets(events, date(2026, 7, 20))

        self.assertEqual(
            targets,
            [
                {
                    "load_target": None,
                    "time_target_hours": 8.0,
                    "sport_type": "Ride",
                    "week_type": "NORMAL",
                }
            ],
        )

    def test_week_phase_lookup_excludes_phase_ending_on_boundary_monday(self):
        events = [
            {
                "category": "PLAN",
                "name": "TdF Alpen",
                "tags": ["Peak"],
                "type": "Ride",
                "start_date_local": "2026-06-15T00:00:00",
                "end_date_local": "2026-07-20T00:00:00",
            }
        ]

        next_week_phases = get_training_plan.find_week_phases(events, date(2026, 7, 20))

        self.assertEqual(next_week_phases, [])

    def test_next_week_without_phase_does_not_inherit_current_phase_in_summary(self):
        monday = date(2026, 7, 13)
        plan_data = {
            "active_phases": [
                {
                    "plan_name": "TdF Alpen",
                    "phase": "Peak",
                    "sport_type": "Ride",
                    "start": "2026-06-15",
                    "end": "2026-07-20",
                }
            ],
            "next_week_active_phases": [],
            "weekly_load_targets": [
                {"sport_type": "Ride", "load_target": 300, "week_type": "NORMAL"}
            ],
            "next_week_load_targets": [
                {"sport_type": "Ride", "load_target": 250, "week_type": "NORMAL"}
            ],
            "weekly_day_constraints": [],
            "next_week_day_constraints": [
                {
                    "date": "2026-07-20",
                    "type": "TRAVEL",
                    "training_allowed": False,
                    "source_category": "NOTE",
                    "source_name": "Rueckreise Frankreich",
                }
            ],
        }

        summary = prepare_week_for_coach._extract_ride_plan_summary(plan_data, monday)

        self.assertEqual(summary[0]["phase"], "Peak")
        self.assertNotIn("phase", summary[1])
        self.assertEqual(summary[1]["weekly_load_target"], 250)
        self.assertEqual(summary[1]["day_constraints"][0]["type"], "TRAVEL")

    def test_next_week_time_target_is_exposed_in_summary(self):
        monday = date(2026, 7, 13)
        plan_data = {
            "active_phases": [],
            "next_week_active_phases": [],
            "weekly_load_targets": [],
            "next_week_load_targets": [
                {
                    "sport_type": "Ride",
                    "load_target": None,
                    "time_target_hours": 8.0,
                    "week_type": "NORMAL",
                }
            ],
            "weekly_day_constraints": [],
            "next_week_day_constraints": [],
        }

        summary = prepare_week_for_coach._extract_ride_plan_summary(plan_data, monday)

        self.assertEqual(summary[0]["weekly_time_target_hours"], 8.0)

    def test_analyze_week_next_week_without_phase_keeps_targets_only(self):
        today = date(2026, 7, 19)
        payload = {
            "active_phases": [
                {
                    "plan_name": "TdF Alpen",
                    "phase": "Peak",
                    "sport_type": "Ride",
                    "start": "2026-06-15",
                    "end": "2026-07-20",
                }
            ],
            "next_week_active_phases": [],
            "weekly_load_targets": [
                {"sport_type": "Ride", "load_target": 300, "week_type": "NORMAL"}
            ],
            "next_week_load_targets": [
                {
                    "sport_type": "Ride",
                    "load_target": 250,
                    "week_type": "RACE",
                    "training_availability": "NORMAL",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            plan_path = output_dir / "training_plan_2026-07-19.json"
            plan_path.write_text(__import__("json").dumps(payload), encoding="utf-8")
            original_output_dir = analyze_week.OUTPUT_DIR
            try:
                analyze_week.OUTPUT_DIR = output_dir
                summary = analyze_week.load_training_plan(today)
            finally:
                analyze_week.OUTPUT_DIR = original_output_dir

        assert summary is not None
        self.assertEqual(summary[0]["phase"], "Peak")
        self.assertNotIn("phase", summary[1])
        self.assertEqual(summary[1]["weekly_load_target"], 250)
        self.assertEqual(summary[1]["week_type"], "RACE")

    def test_analyze_week_keeps_time_target_when_present(self):
        today = date(2026, 7, 19)
        payload = {
            "active_phases": [],
            "next_week_active_phases": [],
            "weekly_load_targets": [],
            "next_week_load_targets": [
                {
                    "sport_type": "Ride",
                    "load_target": None,
                    "time_target_hours": 8.0,
                    "week_type": "NORMAL",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            plan_path = output_dir / "training_plan_2026-07-19.json"
            plan_path.write_text(__import__("json").dumps(payload), encoding="utf-8")
            original_output_dir = analyze_week.OUTPUT_DIR
            try:
                analyze_week.OUTPUT_DIR = output_dir
                summary = analyze_week.load_training_plan(today)
            finally:
                analyze_week.OUTPUT_DIR = original_output_dir

        assert summary is not None
        self.assertEqual(summary[0]["weekly_time_target_hours"], 8.0)


if __name__ == "__main__":
    unittest.main()