import importlib.util
import json
import tempfile
import unittest
from datetime import date, timedelta
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


get_training_plan = _load_module(
    "get_training_plan_history_script",
    "scripts/get_training_plan.py",
)


class TrainingLoadHistoryTests(unittest.TestCase):
    def test_builds_four_completed_ride_weeks(self):
        events = [
            {
                "category": "TARGET",
                "start_date_local": "2026-08-03",
                "type": "Ride",
                "load_target": 418,
            }
        ]
        summaries = {
            "2026-08-03": {
                "byCategory": [
                    {"category": "Ride", "training_load": 510},
                    {"category": "Swim", "training_load": 30},
                ]
            }
        }

        history = get_training_plan.build_training_load_history(
            events,
            summaries,
            date(2026, 8, 10),
        )

        self.assertEqual(len(history), 4)
        self.assertEqual(history[-1], {
            "week_starting": "2026-08-03",
            "weekly_load_target": 418,
            "total_training_load": 510,
            "achievement_pct": 122.0,
        })
        self.assertEqual(history[0]["week_starting"], "2026-07-13")
        self.assertEqual(history[0]["total_training_load"], 0)
        self.assertIsNone(history[0]["weekly_load_target"])
        self.assertIsNone(history[0]["achievement_pct"])

    def test_main_fetches_and_saves_four_completed_weeks(self):
        today = date.today()
        current_monday = today - timedelta(days=today.weekday())
        latest_completed_monday = current_monday - timedelta(weeks=1)
        target_event = {
            "category": "TARGET",
            "start_date_local": latest_completed_monday.isoformat(),
            "type": "Ride",
            "load_target": 400,
        }

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            with (
                patch.object(get_training_plan, "OUTPUT_DIR", output_dir),
                patch.object(
                    get_training_plan,
                    "fetch_all_events",
                    return_value=[target_event],
                ),
                patch.object(
                    get_training_plan,
                    "get_athlete_summary",
                    return_value={
                        "byCategory": [
                            {"category": "Ride", "training_load": 500}
                        ]
                    },
                ) as get_summary,
            ):
                get_training_plan.main()

            output_path = output_dir / f"training_plan_{today.isoformat()}.json"
            output = json.loads(output_path.read_text(encoding="utf-8"))

        expected_ranges = []
        for weeks_ago in range(4, 0, -1):
            week_start = current_monday - timedelta(weeks=weeks_ago)
            expected_ranges.append(
                (
                    get_training_plan.API_KEY,
                    get_training_plan.ATHLETE_ID,
                    week_start.isoformat(),
                    (week_start + timedelta(days=6)).isoformat(),
                )
            )

        self.assertEqual(
            [call.args for call in get_summary.call_args_list],
            expected_ranges,
        )
        self.assertIsInstance(output["training_load_history"], list)
        self.assertEqual(len(output["training_load_history"]), 4)
        self.assertEqual(
            output["training_load_history"][-1],
            {
                "week_starting": latest_completed_monday.isoformat(),
                "weekly_load_target": 400,
                "total_training_load": 500,
                "achievement_pct": 125.0,
            },
        )


if __name__ == "__main__":
    unittest.main()