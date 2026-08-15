import importlib.util
import json
import os
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_mcp_server_module():
    os.environ.setdefault("INTERVALS_API_KEY", "test-key")
    os.environ.setdefault("ATHLETE_ID", "test-athlete")
    module_path = REPO_ROOT / "scripts" / "mcp_server.py"
    spec = importlib.util.spec_from_file_location("local_mcp_server", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class LibraryWorkoutListingTests(unittest.TestCase):
    def test_normalized_workout_includes_library_workout_id(self):
        module = _load_mcp_server_module()

        rows = module._normalize_library_workouts(
            [
                {
                    "id": 81,
                    "folder_id": 438219,
                    "name": "Stored VO2Max",
                    "moving_time": 3600,
                    "icu_training_load": 70,
                    "tags": ["vo2max-moderate"],
                }
            ],
            {438219: "Aerobic-capacity intervals"},
        )

        self.assertEqual(rows[0]["library_workout_id"], 81)

    def test_week_plan_schema_accepts_library_workout_without_steps(self):
        schema = json.loads(
            (REPO_ROOT / "contracts" / "week-plan" / "week-plan.schema.json").read_text(
                encoding="utf-8"
            )
        )
        plan = {
            "workouts": [
                {
                    "date": "2026-05-19",
                    "name": "Stored VO2Max",
                    "duration_minutes": 60,
                    "description": "Stored execution notes",
                    "tags": ["vo2max-moderate"],
                    "library_workout_id": 81,
                }
            ]
        }

        self.assertEqual(list(Draft202012Validator(schema).iter_errors(plan)), [])


if __name__ == "__main__":
    unittest.main()