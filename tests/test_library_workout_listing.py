import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def _load_mcp_server_module():
    os.environ.setdefault("INTERVALS_API_KEY", "test-key")
    os.environ.setdefault("ATHLETE_ID", "test-athlete")
    module_path = REPO_ROOT / "scripts" / "mcp_server.py"
    spec = importlib.util.spec_from_file_location("local_mcp_server", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _load_prepare_activities_module():
    module_path = REPO_ROOT / "scripts" / "prepare_activities_for_coach.py"
    spec = importlib.util.spec_from_file_location("prepare_activities_for_coach_script", module_path)
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

    def test_get_activity_streams_sampled_downsamples_and_filters(self):
        client = __import__("intervals_icu.client", fromlist=["get_activity_streams_sampled"])
        raw = [
            {"type": "time", "data": [0, 10, 20, 30, 40, 50]},
            {"type": "distance", "data": [0.0, 100.0, 200.0, 300.0, 400.0, 500.0]},
            {"type": "altitude", "data": [100, 110, 120, 130, 140, 150]},
            {"type": "heartrate", "data": [120, 130, 140, 150, 160, 170]},
        ]

        def fake_get_activity_streams(api_key, activity_id):
            self.assertEqual(api_key, "test-key")
            self.assertEqual(activity_id, "abc123")
            return raw

        client.get_activity_streams = fake_get_activity_streams

        result = client.get_activity_streams_sampled(
            "test-key",
            "abc123",
            stream_types=["time", "distance", "altitude", "heartrate"],
            max_points=3,
            start_time_s=10,
            end_time_s=40,
            start_distance_m=100.0,
            end_distance_m=400.0,
        )

        self.assertEqual(result["sampled"], True)
        self.assertEqual(result["point_count"], 3)
        self.assertEqual(list(result["streams"].keys()), ["time", "distance", "altitude", "heartrate"])
        self.assertEqual(result["streams"]["time"], [10, 30, 40])
        self.assertEqual(result["streams"]["distance"], [100.0, 300.0, 400.0])
        self.assertEqual(result["streams"]["altitude"], [110, 130, 140])
        self.assertEqual(result["streams"]["heartrate"], [130, 150, 160])

    def test_local_activity_streams_script_exposes_cli_entrypoint(self):
        module_path = REPO_ROOT / "scripts" / "get_activity_streams_sampled.py"
        spec = importlib.util.spec_from_file_location(
            "local_get_activity_streams_sampled_script",
            module_path,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(callable(getattr(module, "main", None)))

    def test_extract_fields_includes_activity_id_and_type(self):
        module = _load_prepare_activities_module()

        activity = {
            "id": "i123456",
            "type": "Ride",
            "start_date_local": "2026-08-16T08:00:00",
            "name": "Test Ride",
            "moving_time": 3600,
            "icu_training_load": 75,
            "icu_average_watts": 220,
            "icu_weighted_avg_watts": 230,
            "icu_zone_times": [],
            "tags": ["threshold"],
            "description": "Ride notes",
            "decoupling": 1.0,
            "icu_rpe": 7,
            "carbs_used": 90,
            "carbs_ingested": 60,
            "icu_w_prime": 20000,
        }

        result = module.extract_fields(activity, wbal_summary=None, power_curve=None, interval_hr_analysis=None)

        self.assertEqual(result["id"], "i123456")
        self.assertEqual(result["type"], "Ride")
        self.assertEqual(list(result)[:2], ["id", "type"])
        self.assertNotIn("activity_id", result)

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