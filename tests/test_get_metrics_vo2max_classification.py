"""Tests for VO2max classification in get_metrics.py."""

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import get_metrics as module
import generate_week_data_schema as contract_generator
from intervals_icu.week_data_schema import Vo2MaxClassification
from jsonschema import Draft202012Validator


class TestVo2maxClassification(unittest.TestCase):
    """Test VO2max classification mapping."""

    def test_male_adult_very_good(self):
        """Male 35-year-old with 50.0 ml/kg/min should be 'very_good'."""
        result = module._build_vo2max_classification(50.0, 35, "Male")
        self.assertIsNotNone(result)
        self.assertEqual(result["category"], "very_good")
        self.assertEqual(result["age_group"], "master_30_39")
        self.assertEqual(result["sex"], "male")
        self.assertEqual(result["ml_per_kg_min"], 50.0)
        self.assertAlmostEqual(result["delta_to_next"], 0.5, places=1)

    def test_male_adult_good(self):
        """Male 35-year-old with 42.0 ml/kg/min should be 'good'."""
        result = module._build_vo2max_classification(42.0, 35, "Male")
        self.assertIsNotNone(result)
        self.assertEqual(result["category"], "good")

    def test_male_adult_average(self):
        """Male 35-year-old with 36.0 ml/kg/min should be 'average'."""
        result = module._build_vo2max_classification(36.0, 35, "Male")
        self.assertIsNotNone(result)
        self.assertEqual(result["category"], "average")

    def test_female_adult_excellent(self):
        """Female 25-year-old with 41.0 ml/kg/min should be 'very_good'."""
        result = module._build_vo2max_classification(41.0, 25, "Female")
        self.assertIsNotNone(result)
        self.assertEqual(result["category"], "very_good")
        self.assertEqual(result["age_group"], "adult_20_29")
        self.assertEqual(result["sex"], "female")

    def test_senior_60_plus(self):
        """Male 65-year-old with 35.0 ml/kg/min should be 'good'."""
        result = module._build_vo2max_classification(35.0, 65, "Male")
        self.assertIsNotNone(result)
        self.assertEqual(result["category"], "good")
        self.assertEqual(result["age_group"], "senior_60_plus")

    def test_teen(self):
        """Teen 16-year-old with 50.0 ml/kg/min should be 'excellent'."""
        result = module._build_vo2max_classification(50.0, 16, "Male")
        self.assertIsNotNone(result)
        self.assertEqual(result["category"], "excellent")
        self.assertEqual(result["age_group"], "teen_13_19")

    def test_missing_vo2max(self):
        """Missing VO2max should return None."""
        result = module._build_vo2max_classification(None, 35, "Male")
        self.assertIsNone(result)

    def test_missing_age(self):
        """Missing age should return None."""
        result = module._build_vo2max_classification(50.0, None, "Male")
        self.assertIsNone(result)

    def test_missing_sex(self):
        """Missing sex should return None."""
        result = module._build_vo2max_classification(50.0, 35, None)
        self.assertIsNone(result)

    def test_next_category_progression(self):
        """Verify next_category progression."""
        result = module._build_vo2max_classification(40.0, 35, "Male")
        self.assertIsNotNone(result)
        self.assertEqual(result["category"], "average")
        self.assertEqual(result["next_category"], "good")
        self.assertGreater(result["delta_to_next"], 0)

    def test_next_category_excellent(self):
        """Excellent category should have no next_category."""
        result = module._build_vo2max_classification(55.0, 35, "Male")
        self.assertIsNotNone(result)
        self.assertEqual(result["category"], "excellent")
        self.assertIsNone(result["next_category"])
        self.assertIsNone(result["delta_to_next"])


class TestVo2maxEstimateRepresentativeness(unittest.TestCase):
    def test_representativeness_bands_use_unrounded_percentage(self):
        cases = [
            (249, 99.6, False),
            (249.9, 100.0, False),
            (250, 100.0, "likely_understated"),
            (260, 104.0, "likely_understated"),
            (262.4, 105.0, "likely_understated"),
            (262.5, 105.0, True),
            (300, 120.0, True),
        ]
        for p5min, percentage, representative in cases:
            with self.subTest(p5min=p5min):
                result = module._build_vo2max_classification(
                    50.0, 35, "Male", p5min_watts=p5min, ftp=250,
                    power_profile_period_days=42,
                )
                self.assertEqual(result["p5min_pct_ftp"], percentage)
                self.assertEqual(result["estimate_representative"], representative)
                self.assertIs(type(result["estimate_representative"]), type(representative))
                self.assertEqual(result["power_profile_period_days"], 42)
                self.assertEqual(
                    result["category"],
                    module._build_vo2max_classification(50.0, 35, "Male")["category"],
                )

    def test_missing_or_unusable_power_inputs(self):
        for p5min, ftp in [
            (None, 250), (300, None), (None, None), (300, 0), (300, -250),
            (float("nan"), 250), (300, float("inf")),
        ]:
            with self.subTest(p5min=p5min, ftp=ftp):
                result = module._build_vo2max_classification(
                    50.0, 35, "Male", p5min_watts=p5min, ftp=ftp,
                )
                self.assertIsNone(result["p5min_pct_ftp"])
                self.assertIsNone(result["estimate_representative"])
                self.assertIsNone(result["power_profile_period_days"])

    def test_main_exports_power_profile_context(self):
        with (
            TemporaryDirectory() as output_dir,
            patch.object(module, "OUTPUT_DIR", Path(output_dir)),
            patch.object(module, "API_KEY", "test-key"),
            patch.object(module, "ATHLETE_ID", "test-athlete"),
            patch.object(module, "fetch_metrics_from_activities", return_value={}),
            patch.object(module, "fetch_athlete_info", return_value=(
                {"ftp": 250, "weight": 70, "age": 35, "sex": "Male"}, False,
            )),
            patch.object(module, "fetch_wellness", return_value={}),
            patch.object(module, "fetch_power_profile", return_value={
                "p5min": {"watts": 240}, "period_days": 28,
            }),
            patch("builtins.print"),
        ):
            module.main()
            payload = json.loads(next(Path(output_dir).glob("metrics_*.json")).read_text())

        classification = payload["vo2max_classification"]
        self.assertEqual(classification["ml_per_kg_min"], 47.0)
        self.assertEqual(classification["p5min_pct_ftp"], 96.0)
        self.assertIs(classification["estimate_representative"], False)
        self.assertEqual(classification["power_profile_period_days"], 28)

    def test_contract_preserves_boolean_string_and_null_states(self):
        schema = Vo2MaxClassification.model_json_schema()
        validator = Draft202012Validator(schema["properties"]["estimate_representative"])
        for state in (False, "likely_understated", True, None):
            with self.subTest(state=state):
                classification = Vo2MaxClassification(estimate_representative=state)
                self.assertEqual(classification.estimate_representative, state)
                self.assertIs(type(classification.estimate_representative), type(state))
                self.assertEqual(
                    json.loads(classification.model_dump_json())["estimate_representative"], state,
                )
                validator.validate(state)
        self.assertFalse(validator.is_valid("true"))
        self.assertFalse(validator.is_valid("unknown"))
        self.assertFalse(validator.is_valid(1))
        field = contract_generator.week_schema.Vo2MaxClassification.model_fields[
            "estimate_representative"
        ]
        self.assertEqual(contract_generator._map_type(field.annotation), ("JsonElement", True))

    def test_generated_contracts_are_current(self):
        contract_dir = Path(__file__).resolve().parents[1] / "contracts" / "week-data"
        self.assertEqual(
            json.loads((contract_dir / "week-data.schema.json").read_text(encoding="utf-8")),
            contract_generator.WeekData.model_json_schema(),
        )
        self.assertEqual(
            (contract_dir / "WeekDataDto.cs").read_text(encoding="utf-8"),
            contract_generator._render_csharp_dtos() + "\n",
        )


if __name__ == "__main__":
    unittest.main()
