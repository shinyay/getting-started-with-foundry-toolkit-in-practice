"""Agent Service memory store definition and drift checks."""

from __future__ import annotations

from typing import Any

from azure.ai.projects.models import (
    MemoryStoreDefaultDefinition,
    MemoryStoreDefaultOptions,
)

MEMORY_TTL_SECONDS = 7 * 24 * 60 * 60
MEMORY_HEALTH_QUERY = "Synthetic tutorial memory health check."
MEMORY_PROFILE_DETAILS = (
    "Store only synthetic tutorial preferences and project facts. "
    "Avoid credentials, secrets, financial data, health data, legal data, "
    "precise locations, and other sensitive or identifying information."
)


def memory_search_items(query: str) -> list[dict[str, str]]:
    """Build the Responses input shape required by Memory search."""
    return [{"type": "message", "role": "user", "content": query}]


def build_memory_definition(
    chat_model: str, embedding_model: str
) -> MemoryStoreDefaultDefinition:
    """Build the intentionally narrow tutorial Memory Store definition."""
    return MemoryStoreDefaultDefinition(
        chat_model=chat_model,
        embedding_model=embedding_model,
        options=MemoryStoreDefaultOptions(
            chat_summary_enabled=False,
            user_profile_enabled=True,
            procedural_memory_enabled=False,
            default_ttl_seconds=MEMORY_TTL_SECONDS,
            user_profile_details=MEMORY_PROFILE_DETAILS,
        ),
    )


def memory_store_drift(
    store: Any, chat_model: str, embedding_model: str
) -> list[str]:
    """Return incompatible settings without mutating an existing store."""
    data = store.as_dict()
    definition = data.get("definition") or {}
    options = definition.get("options") or {}
    expected = {
        "definition.chat_model": (
            definition.get("chat_model"),
            chat_model,
        ),
        "definition.embedding_model": (
            definition.get("embedding_model"),
            embedding_model,
        ),
        "options.user_profile_enabled": (
            options.get("user_profile_enabled"),
            True,
        ),
        "options.chat_summary_enabled": (
            options.get("chat_summary_enabled"),
            False,
        ),
        "options.procedural_memory_enabled": (
            options.get("procedural_memory_enabled"),
            False,
        ),
        "options.default_ttl_seconds": (
            options.get("default_ttl_seconds"),
            MEMORY_TTL_SECONDS,
        ),
    }
    return [
        f"{name}: actual={actual!r}, expected={wanted!r}"
        for name, (actual, wanted) in expected.items()
        if actual != wanted
    ]
