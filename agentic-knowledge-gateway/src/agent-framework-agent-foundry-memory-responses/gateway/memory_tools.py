"""Explicit write-through tools for deterministic synthetic Memory facts."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from azure.ai.projects.models import MemoryItemKind

from .memory_proof import MemoryProof
from .settings import GatewaySettings


def create_memory_tools(
    project_client: Any,
    settings: GatewaySettings,
) -> list[Callable[..., Awaitable[str]]]:
    """Create tools that share the Gateway's authenticated Project client."""

    async def remember_synthetic_association(
        key: str,
        value: str,
    ) -> str:
        """Persist one exact synthetic tutorial association.

        Args:
            key: An opaque key using ``akg`` plus 16 hexadecimal characters.
            value: An independent value using ``akv`` plus 16 hexadecimal
                characters.
        """
        proof = MemoryProof(key, value)
        item = await project_client.beta.memory_stores.create_memory(
            name=settings.memory_store_name,
            scope=settings.memory_scope,
            content=proof.pair,
            kind=MemoryItemKind.USER_PROFILE,
        )
        if item.content != proof.pair:
            raise RuntimeError(
                "The memory store did not preserve the synthetic association "
                "exactly."
            )
        return f"Stored exact synthetic association: {proof.pair}"

    return [remember_synthetic_association]
