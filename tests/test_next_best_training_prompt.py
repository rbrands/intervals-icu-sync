import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from src.intervals_icu.prompt_templates import render_coach_prompt


ROOT = Path(__file__).resolve().parents[1]


class NextBestTrainingPromptTests(unittest.TestCase):
    def test_short_output_and_upload_contract(self):
        prompt = render_coach_prompt("next_best_training", "de")
        for requirement in (
            "At most 100 words of prose",
            "exactly one workout",
            "The alternative stays in prose only",
            "system prompt's\n  existing schema, markers, and TSS rules",
            "Upload only after the user explicitly\n  requests it",
            "existing weekly-plan workflow",
            "Do not upload automatically or ask for confirmation now",
            "system prompt's prose-only rule",
            "`current_date`",
            "calendar day",
            "Do not treat today's readiness as tomorrow's",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, prompt)
        self.assertNotIn("One sentence of reasoning per decision factor", prompt)
        self.assertNotIn("duration_seconds", prompt)
        self.assertTrue(prompt.endswith("Please respond in de."))

    def test_local_and_hosted_upload_workflows_require_validation(self):
        prompt = render_coach_prompt("next_best_training", "en")
        local, hosted = prompt.split("local MCP: ", 1)[1].split("hosted MCP: ", 1)
        self.assertIn(
            "save_week_plan(plan_json=...), then validate_week_plan(), then\n"
            "  upload_week_plan()",
            local,
        )
        self.assertIn(
            "validate_week_plan(plan_json=...), then\n"
            "  upload_week_plan(plan_json=...) with the same JSON (no save tool)",
            hosted,
        )
        self.assertIn("Upload only if validation succeeds.", hosted)

    def test_documented_english_prompt_matches_template(self):
        library = (ROOT / "docs/prompt_library.md").read_text(encoding="utf-8")
        template = (
            ROOT / "prompts/library/07_next_best_training.md"
        ).read_text(encoding="utf-8").strip()
        self.assertIn(template, library)

    def test_single_workout_and_rest_match_existing_upload_schema(self):
        schema = json.loads(
            (ROOT / "contracts/week-plan/week-plan.schema.json").read_text(
                encoding="utf-8"
            )
        )
        validator = Draft202012Validator(schema)
        workout = {
            "date": "2026-10-16",
            "name": "Easy Endurance",
            "duration_minutes": 60,
            "activity_type": "Ride",
            "description": "Easy endurance, 41 TSS, 30 g carbs/h.",
            "tss": 41,
            "tags": ["aerobic-threshold-low"],
            "steps": [
                {"duration_seconds": 600, "power_pct_ftp": 50},
                {"duration_seconds": 2400, "power_pct_ftp": 70},
                {"duration_seconds": 600, "power_pct_ftp": 50},
            ],
        }
        validator.validate({"workouts": [workout]})
        validator.validate({"workouts": []})
        self.assertEqual(
            sum(step["duration_seconds"] for step in workout["steps"]),
            workout["duration_minutes"] * 60,
        )
        self.assertEqual(
            round(sum(
                step["duration_seconds"] / 3600
                * (step["power_pct_ftp"] / 100) ** 2 * 100
                for step in workout["steps"]
            )),
            workout["tss"],
        )


if __name__ == "__main__":
    unittest.main()
