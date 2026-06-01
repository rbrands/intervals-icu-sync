import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKOUTS_FILE = REPO_ROOT / "coach-logic" / "workouts.md"

EXPECTED_PREFIXES = {
    "vo2max",
    "lactate-treshold",
    "aerobic-treshold",
    "race-specific",
}
EXPECTED_SUFFIXES = {"high", "moderate", "low"}


class WorkoutTagConventionTests(unittest.TestCase):
    def _read_tag_values(self) -> list[str]:
        content = WORKOUTS_FILE.read_text(encoding="utf-8")
        tags = re.findall(r"\*\*Tag:\*\*\s+([a-z0-9-]+)", content)
        self.assertGreater(len(tags), 0, "No workout tags found in workouts.md")
        return tags

    def test_all_tags_use_expected_pattern(self):
        for tag in self._read_tag_values():
            self.assertRegex(
                tag,
                r"^[a-z0-9-]+-(high|moderate|low)$",
                msg=f"Invalid workout tag format: {tag}",
            )

    def test_all_tags_use_known_prefixes(self):
        for tag in self._read_tag_values():
            prefix, _, suffix = tag.rpartition("-")
            self.assertIn(prefix, EXPECTED_PREFIXES, msg=f"Unknown workout tag prefix: {prefix}")
            self.assertIn(suffix, EXPECTED_SUFFIXES, msg=f"Unknown workout tag suffix: {suffix}")

    def test_each_prefix_has_all_dose_levels(self):
        tags = self._read_tag_values()
        found_by_prefix: dict[str, set[str]] = {prefix: set() for prefix in EXPECTED_PREFIXES}

        for tag in tags:
            prefix, _, suffix = tag.rpartition("-")
            if prefix in found_by_prefix and suffix in EXPECTED_SUFFIXES:
                found_by_prefix[prefix].add(suffix)

        for prefix, found_suffixes in found_by_prefix.items():
            self.assertEqual(
                found_suffixes,
                EXPECTED_SUFFIXES,
                msg=(
                    f"Prefix '{prefix}' must define all dose levels "
                    f"{sorted(EXPECTED_SUFFIXES)} but found {sorted(found_suffixes)}"
                ),
            )


if __name__ == "__main__":
    unittest.main()
