import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gateway.app import run_gateway
from gateway.settings import GatewaySettings

SETTINGS = GatewaySettings(
    project_endpoint="https://example.test/api/projects/demo",
    model_deployment="chat",
    memory_store_name="memory",
    memory_scope="scope",
)


class AppLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_credential_closes_when_client_construction_fails(
        self,
    ) -> None:
        credential = MagicMock()
        credential.close = AsyncMock()
        with (
            patch(
                "gateway.app.DefaultAzureCredential",
                return_value=credential,
            ),
            patch(
                "gateway.app.FoundryChatClient",
                side_effect=RuntimeError("construction failed"),
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "construction failed",
            ):
                await run_gateway(SETTINGS)
        credential.close.assert_awaited_once()

    async def test_runtime_wires_exact_memory_tool(self) -> None:
        credential = MagicMock()
        credential.close = AsyncMock()
        project = MagicMock()
        project.close = AsyncMock()
        project.beta.memory_stores.get = AsyncMock(
            return_value=MagicMock(name="memory")
        )
        project.beta.memory_stores.search_memories = AsyncMock()
        client = MagicMock(project_client=project)
        server = MagicMock()
        server.run_async = AsyncMock()
        tool = AsyncMock()

        with (
            patch(
                "gateway.app.DefaultAzureCredential",
                return_value=credential,
            ),
            patch(
                "gateway.app.FoundryChatClient",
                return_value=client,
            ),
            patch("gateway.app.GatewayMemoryProvider"),
            patch(
                "gateway.app.create_memory_tools",
                return_value=[tool],
            ),
            patch("gateway.app.Agent") as agent_type,
            patch(
                "gateway.app.ResponsesHostServer",
                return_value=server,
            ),
        ):
            await run_gateway(SETTINGS)

        self.assertEqual(agent_type.call_args.kwargs["tools"], [tool])
        server.run_async.assert_awaited_once()
        project.close.assert_awaited_once()
        credential.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
