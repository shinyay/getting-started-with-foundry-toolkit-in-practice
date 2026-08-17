import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from agent_framework.foundry import FoundryMemoryProvider

from gateway.memory_proof import contains_memory_proof_pair
from gateway.memory_provider import GatewayMemoryProvider


class MemoryProviderTests(unittest.IsolatedAsyncioTestCase):
    def test_complete_pair_detection_is_strict(self) -> None:
        self.assertTrue(
            contains_memory_proof_pair(
                "Remember akg0123456789abcdef=akvfedcba9876543210."
            )
        )
        self.assertFalse(
            contains_memory_proof_pair("Recall akg0123456789abcdef.")
        )

    async def test_exact_pair_skips_semantic_after_update(self) -> None:
        provider = object.__new__(GatewayMemoryProvider)
        context = SimpleNamespace(
            input_messages=[
                SimpleNamespace(
                    role="user",
                    text=(
                        "Remember "
                        "akg0123456789abcdef=akvfedcba9876543210."
                    ),
                )
            ]
        )
        with patch.object(
            FoundryMemoryProvider,
            "after_run",
            new=AsyncMock(),
        ) as base_after_run:
            await provider.after_run(
                agent=MagicMock(),
                session=MagicMock(),
                context=context,
                state={},
            )
        base_after_run.assert_not_awaited()

    async def test_ordinary_message_keeps_semantic_after_update(self) -> None:
        provider = object.__new__(GatewayMemoryProvider)
        agent = MagicMock()
        session = MagicMock()
        context = SimpleNamespace(
            input_messages=[
                SimpleNamespace(
                    role="user",
                    text="Remember that I prefer concise bullet points.",
                )
            ]
        )
        state: dict[str, object] = {}
        with patch.object(
            FoundryMemoryProvider,
            "after_run",
            new=AsyncMock(),
        ) as base_after_run:
            await provider.after_run(
                agent=agent,
                session=session,
                context=context,
                state=state,
            )
        base_after_run.assert_awaited_once_with(
            agent=agent,
            session=session,
            context=context,
            state=state,
        )


if __name__ == "__main__":
    unittest.main()
