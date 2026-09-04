import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class DeployPackageRegressionTests(unittest.TestCase):
    def test_deploy_workflow_includes_contracts_in_zip_package(self):
        workflow = (REPO_ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        self.assertIn("cp -R contracts/.            _deploy/contracts/", workflow)
