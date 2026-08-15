import unittest

from gateway.settings import (
    A2ASettings,
    GatewaySettings,
    ProvisioningSettings,
)


BASE = {
    "FOUNDRY_PROJECT_ENDPOINT": "https://example.test/project",
    "AZURE_AI_MODEL_DEPLOYMENT_NAME": "gpt-5.4-mini",
    "AZURE_AI_EMBEDDING_MODEL_DEPLOYMENT_NAME": (
        "text-embedding-3-small"
    ),
    "MEMORY_STORE_NAME": "tutorial-memory",
    "MEMORY_SCOPE": "akg-tutorial-scope",
    "FOUNDRY_HOSTED_AGENT_NAME": "agentic-knowledge-gateway",
}


class SettingsTests(unittest.TestCase):
    def test_gateway_settings_load_required_values(self) -> None:
        settings = GatewaySettings.from_env(BASE)
        self.assertEqual(settings.memory_scope, "akg-tutorial-scope")

    def test_missing_setting_is_rejected(self) -> None:
        values = dict(BASE)
        values.pop("MEMORY_SCOPE")
        with self.assertRaisesRegex(ValueError, "MEMORY_SCOPE"):
            GatewaySettings.from_env(values)

    def test_unresolved_placeholder_is_rejected(self) -> None:
        values = dict(BASE)
        values["MEMORY_STORE_NAME"] = "${MEMORY_STORE_NAME}"
        with self.assertRaisesRegex(ValueError, "MEMORY_STORE_NAME"):
            GatewaySettings.from_env(values)

    def test_tool_settings_extend_runtime_settings(self) -> None:
        provisioning = ProvisioningSettings.from_env(BASE)
        a2a = A2ASettings.from_env(BASE)
        self.assertEqual(
            provisioning.embedding_model_deployment,
            "text-embedding-3-small",
        )
        self.assertEqual(a2a.agent_name, "agentic-knowledge-gateway")


if __name__ == "__main__":
    unittest.main()
