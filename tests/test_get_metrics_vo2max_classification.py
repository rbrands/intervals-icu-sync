"""Tests for VO2max classification in get_metrics.py."""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import get_metrics as module


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


if __name__ == "__main__":
    unittest.main()
