import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from gateway.settings import A2ASettings, GatewaySettings
from scripts.configure_a2a import configure

GATEWAY = GatewaySettings(
    project_endpoint="https://example.test/api/projects/demo",
    model_deployment="chat",
    memory_store_name="memory",
    memory_scope="scope",
)
SETTINGS = A2ASettings(
    gateway=GATEWAY,
    agent_name="gateway",
)


class ConfigureA2ATests(unittest.TestCase):
    def test_credential_closes_when_client_construction_fails(self) -> None:
        credential = MagicMock()

        with (
            patch(
                "scripts.configure_a2a.A2ASettings.from_env",
                return_value=SETTINGS,
            ),
            patch(
                "scripts.configure_a2a.DefaultAzureCredential",
                return_value=credential,
            ),
            patch(
                "scripts.configure_a2a.AIProjectClient",
                side_effect=RuntimeError("construction failed"),
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "construction failed",
            ):
                configure()

        credential.close.assert_called_once()

    def test_project_client_enables_preview(self) -> None:
        credential = MagicMock()
        credential.get_token.return_value = SimpleNamespace(token="token")
        project = MagicMock()
        response = MagicMock()
        response.json.return_value = {
            "supportedInterfaces": [
                {
                    "protocolBinding": "JSONRPC",
                    "protocolVersion": "1.0",
                }
            ]
        }

        with (
            patch(
                "scripts.configure_a2a.A2ASettings.from_env",
                return_value=SETTINGS,
            ),
            patch(
                "scripts.configure_a2a.DefaultAzureCredential",
                return_value=credential,
            ),
            patch(
                "scripts.configure_a2a.AIProjectClient",
                return_value=project,
            ) as project_type,
            patch("scripts.configure_a2a.httpx.get", return_value=response),
        ):
            configure()

        project_type.assert_called_once_with(
            endpoint=GATEWAY.project_endpoint,
            credential=credential,
            allow_preview=True,
        )
        project.agents.update_details.assert_called_once()
        project.close.assert_called_once()
        credential.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
