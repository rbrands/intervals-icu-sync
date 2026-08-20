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
get_metrics = _load_module(
    "get_metrics_history_script",
    "scripts/get_metrics.py",
)
prepare_week_for_coach = _load_module(
    "prepare_week_for_coach_history_script",
    "scripts/prepare_week_for_coach.py",
)


class TrainingLoadHistoryTests(unittest.TestCase):
    def test_merges_weekly_readiness_into_load_history(self):
        history = prepare_week_for_coach.merge_training_load_history(
            [{"week_starting": "2026-08-03", "total_training_load": 500}],
            [{
                "week_starting": "2026-08-03",
                "ctl": 58.4,
                "atl": 63.1,
                "form_absolute": -4.7,
                "form_pct": -0.0805,
                "form_percent_display": -8.1,
            }],
        )

        self.assertEqual(history, [{
            "week_starting": "2026-08-03",
            "total_training_load": 500,
            "ctl": 58.4,
            "atl": 63.1,
            "form_absolute": -4.7,
            "form_pct": -0.0805,
            "form_percent_display": -8.1,
        }])

    def test_builds_compact_weekly_ctl_atl_form_snapshots(self):
        entries = [
            {"id": "2026-07-19", "ctl": 50.04, "atl": 45.06},
            {"id": "2026-07-26", "ctl": 52.04, "atl": 56.06},
            {"id": "2026-08-01", "ctl": 55.04, "atl": 47.06},
        ]

        history = get_metrics.build_training_load_history(
            entries,
            current_monday=date(2026, 8, 10),
        )

        self.assertEqual(history, [
            {
                "week_starting": "2026-07-13",
                "ctl": 50.0,
                "atl": 45.1,
                "form_absolute": 5.0,
                "form_pct": 0.0995,
                "form_percent_display": 10.0,
            },
            {
                "week_starting": "2026-07-20",
                "ctl": 52.0,
                "atl": 56.1,
                "form_absolute": -4.0,
                "form_pct": -0.0772,
                "form_percent_display": -7.7,
            },
            {
                "week_starting": "2026-07-27",
                "ctl": 55.0,
                "atl": 47.1,
                "form_absolute": 8.0,
                "form_pct": 0.145,
                "form_percent_display": 14.5,
            },
            {
                "week_starting": "2026-08-03",
                "ctl": None,
                "atl": None,
                "form_absolute": None,
                "form_pct": None,
                "form_percent_display": None,
            },
        ])

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