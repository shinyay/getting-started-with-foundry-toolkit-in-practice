import unittest
from pathlib import Path

import yaml

SOURCE_ROOT = Path(__file__).resolve().parents[1]
GATEWAY_ROOT = Path(__file__).resolve().parents[3]


class ProjectFileTests(unittest.TestCase):
    def test_deployment_names_are_valid_arm_literals(self) -> None:
        manifest = yaml.safe_load(
            (GATEWAY_ROOT / "azure.yaml").read_text(encoding="utf-8")
        )
        deployments = manifest["services"]["ai-project"]["deployments"]
        self.assertEqual(
            [item["name"] for item in deployments],
            [
                "gpt-5.4-mini",
                "text-embedding-3-small",
            ],
        )

    def test_optional_dockerfile_uses_python_313(self) -> None:
        first_line = (
            (SOURCE_ROOT / "Dockerfile")
            .read_text(encoding="utf-8")
            .splitlines()[0]
        )
        self.assertEqual(first_line, "FROM python:3.13-slim")

    def test_a2a_client_uses_bearer_token(self) -> None:
        source = (
            SOURCE_ROOT / "scripts" / "a2a_client.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            'headers={"Authorization": f"Bearer {token}"}',
            source,
        )

    def test_generated_metadata_is_ignored(self) -> None:
        ignore = (GATEWAY_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("**/.foundry/agent-metadata.yaml", ignore)
        self.assertIn(
            "!**/.foundry/agent-metadata.example.yaml",
            ignore,
        )

    def test_metadata_example_contains_no_live_endpoint(self) -> None:
        example = yaml.safe_load(
            (
                SOURCE_ROOT
                / ".foundry"
                / "agent-metadata.example.yaml"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            example["environments"]["dev"]["projectEndpoint"],
            "https://<account>.services.ai.azure.com/api/projects/<project>",
        )

    def test_agents_command_changes_to_source_root(self) -> None:
        instructions = (GATEWAY_ROOT / "AGENTS.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "cd src/agent-framework-agent-foundry-memory-responses",
            instructions,
        )
        self.assertIn(
            "../../.venv/bin/python -m unittest discover -s tests -v",
            instructions,
        )


if __name__ == "__main__":
    unittest.main()
