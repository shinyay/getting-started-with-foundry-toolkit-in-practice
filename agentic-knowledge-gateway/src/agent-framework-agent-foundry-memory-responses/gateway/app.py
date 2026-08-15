"""Gateway composition and Hosted Responses server."""

from __future__ import annotations

import logging

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient, FoundryMemoryProvider
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity.aio import DefaultAzureCredential

from .memory_config import MEMORY_HEALTH_QUERY, memory_search_items
from .settings import GatewaySettings

logger = logging.getLogger(__name__)

AGENT_INSTRUCTIONS = """
You are a tutorial Agentic Knowledge Gateway.

Use relevant Foundry Memory items when answering. You may remember and recall
only synthetic tutorial preferences and project facts. Do not ask for or claim
to store credentials, secrets, financial data, health data, legal data, precise
locations, or other sensitive information. If a user supplies sensitive data,
tell them this tutorial is for synthetic test data only.

The configured Memory scope is shared tutorial state, not a private per-user
store. Keep answers concise, state when remembered context influenced an
answer, and never claim that caller identity provides Memory isolation.
""".strip()


async def run_gateway(settings: GatewaySettings) -> None:
    """Verify Memory access, compose the Agent, and run the server."""
    credential = DefaultAzureCredential()
    client = FoundryChatClient(
        project_endpoint=settings.project_endpoint,
        model=settings.model_deployment,
        credential=credential,
        allow_preview=True,
    )

    try:
        store = await client.project_client.beta.memory_stores.get(
            name=settings.memory_store_name
        )
        await client.project_client.beta.memory_stores.search_memories(
            name=settings.memory_store_name,
            scope=settings.memory_scope,
            items=memory_search_items(MEMORY_HEALTH_QUERY),
        )
        logger.info(
            "Verified Memory Store access: store=%s scope=%s",
            store.name,
            settings.memory_scope,
        )

        memory_provider = FoundryMemoryProvider(
            project_client=client.project_client,
            memory_store_name=settings.memory_store_name,
            scope=settings.memory_scope,
            update_delay=0,
        )
        agent = Agent(
            name="AgenticKnowledgeGateway",
            client=client,
            instructions=AGENT_INSTRUCTIONS,
            context_providers=[memory_provider],
            default_options={"store": False},
        )
        server = ResponsesHostServer(agent)
        await server.run_async()
    finally:
        await client.project_client.close()
        await credential.close()
