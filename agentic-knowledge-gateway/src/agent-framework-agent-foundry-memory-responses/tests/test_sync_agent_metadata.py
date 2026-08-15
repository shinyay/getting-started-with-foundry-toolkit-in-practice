import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.sync_agent_metadata import (
    build_metadata,
    render_metadata,
    write_metadata_atomic,
)

TEMPLATE = {
    "defaultEnvironment": "dev",
    "environments": {
        "dev": {
            "projectEndpoint": "https://<account>/api/projects/<project>",
            "agentName": "agentic-knowledge-gateway",
            "agentVersion": "<generated>",
            "region": "<region>",
            "deploymentMode": "code-remote-build",
            "protocols": {"responses": "2.0.0", "a2a": "1.0"},
            "memory": {
                "storeName": "memory",
                "scope": "scope",
                "defaultTtlSeconds": 604800,
            },
            "testCases": [{"id": "smoke-core"}],
        }
    },
}
VALUES = {
    "FOUNDRY_HOSTED_AGENT_NAME": "agentic-knowledge-gateway",
    "AGENT_AGENTIC_KNOWLEDGE_GATEWAY_PROJECT_ENDPOINT": (
        "https://example.test/api/projects/demo"
    ),
    "AGENT_AGENTIC_KNOWLEDGE_GATEWAY_VERSION": "3",
    "AZURE_LOCATION": "eastus2",
    "MEMORY_STORE_NAME": "memory",
    "MEMORY_SCOPE": "scope",
    "AZURE_AI_MODEL_DEPLOYMENT_NAME": "chat",
    "AZURE_AI_EMBEDDING_MODEL_DEPLOYMENT_NAME": "embedding",
}


class AgentMetadataTests(unittest.TestCase):
    def test_dynamic_values_replace_placeholders(self) -> None:
        metadata = build_metadata(TEMPLATE, VALUES, "dev")
        selected = metadata["environments"]["dev"]
        self.assertEqual(
            selected["projectEndpoint"],
            VALUES["AGENT_AGENTIC_KNOWLEDGE_GATEWAY_PROJECT_ENDPOINT"],
        )
        self.assertEqual(selected["agentVersion"], "3")
        self.assertEqual(
            selected["models"]["embeddingDeployment"],
            "embedding",
        )

    def test_cached_test_cases_are_preserved(self) -> None:
        metadata = build_metadata(TEMPLATE, VALUES, "dev")
        self.assertEqual(
            metadata["environments"]["dev"]["testCases"],
            [{"id": "smoke-core"}],
        )

    def test_missing_deployment_version_is_rejected(self) -> None:
        values = dict(VALUES)
        values.pop("AGENT_AGENTIC_KNOWLEDGE_GATEWAY_VERSION")
        with self.assertRaisesRegex(ValueError, "VERSION"):
            build_metadata(TEMPLATE, values, "dev")

    def test_atomic_writer_produces_valid_yaml(self) -> None:
        metadata = build_metadata(TEMPLATE, VALUES, "dev")
        content = render_metadata(metadata)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "agent-metadata.yaml"
            write_metadata_atomic(path, content)
            parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertEqual(parsed, metadata)
            self.assertFalse(
                (path.parent / ".agent-metadata.yaml.tmp").exists()
            )


if __name__ == "__main__":
    unittest.main()
