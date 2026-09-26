import importlib.util
from pathlib import Path
import unittest


_REPO_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = _REPO_ROOT / "foundry-agent" / "deploy_agent.py"


spec = importlib.util.spec_from_file_location("deploy_agent", _MODULE_PATH)
deploy_agent = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(deploy_agent)


class DeployAgentTests(unittest.TestCase):
    def test_staging_config_inherits_agent_and_uses_isolated_resources(self):
        production = deploy_agent._load_agent_definition()
        staging = deploy_agent._load_agent_definition(
            _REPO_ROOT / "foundry-agent" / "agent-staging.yaml"
        )

        self.assertEqual(production["definition"]["model"], "gpt-5.6-luna")
        self.assertEqual(staging["name"], "training-architect-agent-staging")
        self.assertEqual(staging["definition"]["model"], production["definition"]["model"])
        self.assertEqual(
            staging["definition"]["instructions"],
            production["definition"]["instructions"],
        )
        self.assertEqual(staging["deployment"]["vector_store_name"], "coach-logic-staging")
        self.assertEqual(
            staging["deployment"]["skill_name"], "training-plan-generation-staging"
        )
        self.assertEqual(
            staging["deployment"]["toolbox_name"], "training-plan-toolbox-staging"
        )

    def test_embed_discipline_profiles_replaces_placeholder(self):
        rendered = deploy_agent._embed_discipline_profiles(
            f"before\n{deploy_agent._PROFILES_PLACEHOLDER}\nafter"
        )

        self.assertNotIn(deploy_agent._PROFILES_PLACEHOLDER, rendered)
        self.assertIn("before", rendered)
        self.assertIn("after", rendered)

        for discipline in deploy_agent._DISCIPLINES:
            self.assertIn(f"### {discipline}", rendered)


if __name__ == "__main__":
    unittest.main()
