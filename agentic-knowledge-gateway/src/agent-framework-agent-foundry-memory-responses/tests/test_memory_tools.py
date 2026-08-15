import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from azure.ai.projects.models import MemoryItemKind

from gateway.memory_tools import create_memory_tools
from gateway.settings import GatewaySettings

KEY = "akg0123456789abcdef"
VALUE = "akvfedcba9876543210"
PAIR = f"{KEY}={VALUE}"
SETTINGS = GatewaySettings(
    project_endpoint="https://example.test/api/projects/demo",
    model_deployment="chat",
    memory_store_name="memory",
    memory_scope="scope",
)


def fake_project(content: str = PAIR) -> tuple[object, AsyncMock]:
    create_memory = AsyncMock(
        return_value=SimpleNamespace(content=content)
    )
    project = SimpleNamespace(
        beta=SimpleNamespace(
            memory_stores=SimpleNamespace(create_memory=create_memory)
        )
    )
    return project, create_memory


class MemoryToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_tool_writes_one_exact_user_profile_item(self) -> None:
        project, create_memory = fake_project()
        tool = create_memory_tools(project, SETTINGS)[0]

        result = await tool(KEY, VALUE)

        create_memory.assert_awaited_once_with(
            name="memory",
            scope="scope",
            content=PAIR,
            kind=MemoryItemKind.USER_PROFILE,
        )
        self.assertIn(PAIR, result)

    async def test_tool_rejects_non_synthetic_input(self) -> None:
        project, create_memory = fake_project()
        tool = create_memory_tools(project, SETTINGS)[0]

        with self.assertRaises(ValueError):
            await tool("customer-key", VALUE)

        create_memory.assert_not_awaited()

    async def test_tool_rejects_non_verbatim_service_result(self) -> None:
        project, _ = fake_project(f"Stored pair: {PAIR}")
        tool = create_memory_tools(project, SETTINGS)[0]

        with self.assertRaisesRegex(RuntimeError, "preserve"):
            await tool(KEY, VALUE)


if __name__ == "__main__":
    unittest.main()
