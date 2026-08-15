import unittest
from pathlib import Path

from src.intervals_icu.prompt_templates import render_coach_prompt


REPO_ROOT = Path(__file__).resolve().parents[1]


class LibraryWorkoutPromptContractTests(unittest.TestCase):
    def test_plan_prompt_templates_require_single_batched_lookup_and_fallback(self):
        for prompt_name in (
            "training_plan_generation_manual",
            "training_plan_generation_automatic",
        ):
            with self.subTest(prompt_name=prompt_name):
                prompt = render_coach_prompt(prompt_name, "en")
                self.assertIn("exactly once", prompt)
                self.assertIn("list_library_workouts", prompt)
                self.assertIn("no matching workout", prompt)
                self.assertIn("library_workout_id", prompt)

    def test_system_prompts_leave_library_orchestration_to_plan_prompts(self):
        system_prompts = [
            (REPO_ROOT / "foundry-agent" / "agent.yaml").read_text(encoding="utf-8"),
            (REPO_ROOT / "prompts" / "system_prompt.md").read_text(encoding="utf-8"),
        ]
        for prompt in system_prompts:
            with self.subTest():
                self.assertNotIn("exactly once per generated plan", prompt)
                self.assertNotIn("Library Workout Lookup (CRITICAL)", prompt)

    def test_documented_plan_prompts_include_library_lookup_and_fallback(self):
        prompt_library = (REPO_ROOT / "docs" / "prompt_library.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(prompt_library.count("`list_library_workouts`"), 8)
        self.assertEqual(prompt_library.count("`library_workout_id`"), 8)
        self.assertEqual(prompt_library.count("include_untagged=false"), 4)
        self.assertEqual(prompt_library.count("Final self-check before returning output"), 2)
        self.assertEqual(prompt_library.count("Abschließender Selbstcheck vor der Ausgabe"), 2)
        self.assertEqual(prompt_library.count("TSS Calculation rules"), 2)
        self.assertEqual(prompt_library.count("Regeln zur TSS-Berechnung"), 2)


if __name__ == "__main__":
    unittest.main()