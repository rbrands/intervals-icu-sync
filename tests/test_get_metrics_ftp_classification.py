import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_get_metrics_module():
    module_path = REPO_ROOT / "scripts" / "get_metrics.py"
    spec = importlib.util.spec_from_file_location("get_metrics_script", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class FtpClassificationTests(unittest.TestCase):
    def test_grand_master_male_classification_matches_table_example(self):
        module = _load_get_metrics_module()

        result = module._build_ftp_classification(3.53, 55, "Male")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["w_per_kg"], 3.53)
        self.assertEqual(result["age_group"], "grand_master_50_59")
        self.assertEqual(result["sex"], "male")
        self.assertEqual(result["category"], "ambitious_amateur")
        self.assertEqual(result["category_range"], {"min": 3.1, "max": 4.1})
        self.assertEqual(result["next_category"], "performance_oriented")
        self.assertEqual(result["delta_to_next"], 0.57)

    def test_returns_none_when_required_inputs_missing(self):
        module = _load_get_metrics_module()

        self.assertIsNone(module._build_ftp_classification(None, 45, "Male"))
        self.assertIsNone(module._build_ftp_classification(3.2, None, "Male"))
        self.assertIsNone(module._build_ftp_classification(3.2, 45, None))


if __name__ == "__main__":
    unittest.main()
