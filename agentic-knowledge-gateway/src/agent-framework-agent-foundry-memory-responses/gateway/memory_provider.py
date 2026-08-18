"""Memory provider behavior for deterministic tutorial proofs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_framework.foundry import FoundryMemoryProvider

from .memory_proof import contains_memory_proof_pair

if TYPE_CHECKING:
    from agent_framework import AgentSession, SessionContext, SupportsAgentRun


class GatewayMemoryProvider(FoundryMemoryProvider):
    """Keep semantic updates from rewriting a direct exact-pair write."""

    async def after_run(
        self,
        *,
        agent: SupportsAgentRun,
        session: AgentSession,
        context: SessionContext,
        state: dict[str, Any],
    ) -> None:
        if any(
            message.role == "user"
            and message.text
            and contains_memory_proof_pair(message.text)
            for message in context.input_messages
        ):
            return
        await super().after_run(
            agent=agent,
            session=session,
            context=context,
            state=state,
        )
