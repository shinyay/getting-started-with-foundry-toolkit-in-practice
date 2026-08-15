"""Run the tutorial remember/recall flow through incoming A2A v1.0."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import new_text_message
from a2a.types.a2a_pb2 import Role, SendMessageRequest
from azure.ai.projects.aio import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.identity.aio import DefaultAzureCredential as AsyncCredential
from dotenv import load_dotenv
from google.protobuf.json_format import MessageToDict

from gateway.a2a_config import a2a_base_url, has_v1_jsonrpc_interface
from gateway.memory_config import memory_search_items
from gateway.settings import A2ASettings
from scripts.memory_proof import (
    create_marker,
    has_memory_proof,
    recall_query,
    remember_message,
)

MEMORY_POLL_TIMEOUT_SECONDS = 300


async def wait_for_memory(
    settings: A2ASettings,
    marker: str,
) -> None:
    """Poll the authoritative Memory API instead of trusting agent prose."""
    deadline = time.monotonic() + MEMORY_POLL_TIMEOUT_SECONDS
    gateway = settings.gateway
    async with (
        AsyncCredential() as credential,
        AIProjectClient(
            endpoint=gateway.project_endpoint,
            credential=credential,
            allow_preview=True,
        ) as project,
    ):
        while time.monotonic() < deadline:
            result = await project.beta.memory_stores.search_memories(
                name=gateway.memory_store_name,
                scope=gateway.memory_scope,
                items=memory_search_items(recall_query(marker)),
            )
            contents = [
                item.memory_item.content
                for item in result.memories
            ]
            if has_memory_proof(contents, marker):
                print(
                    "Verified this run's synthetic fact in Foundry Memory."
                )
                return
            await asyncio.sleep(5)
    raise TimeoutError("The synthetic fact did not appear in Memory.")


def response_text(response: Any) -> str:
    """Extract text artifacts from an A2A protobuf response."""
    payload = MessageToDict(response, preserving_proto_field_name=True)
    texts: list[str] = []
    for artifact in payload.get("task", {}).get("artifacts", []):
        texts.extend(
            part["text"]
            for part in artifact.get("parts", [])
            if part.get("text")
        )
    texts.extend(
        part["text"]
        for part in payload.get("message", {}).get("parts", [])
        if part.get("text")
    )
    if not texts:
        raise RuntimeError("The A2A response contained no text output.")
    return "\n".join(texts)


async def send_text(client: Any, text: str) -> str:
    message = new_text_message(text, role=Role.ROLE_USER)
    request = SendMessageRequest(message=message)
    chunks: list[str] = []
    async for response in client.send_message(request):
        rendered = response_text(response)
        chunks.append(rendered)
        print(rendered, flush=True)
    return "\n".join(chunks)


async def run() -> None:
    settings = A2ASettings.from_env()
    gateway = settings.gateway
    marker = create_marker()
    print(f"Verification marker: {marker}")
    base_url = a2a_base_url(
        gateway.project_endpoint, settings.agent_name
    )
    credential = DefaultAzureCredential()
    try:
        token = credential.get_token(
            "https://ai.azure.com/.default"
        ).token
        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {token}"},
            timeout=httpx.Timeout(120.0),
        ) as http_client:
            resolver = A2ACardResolver(
                httpx_client=http_client,
                base_url=base_url,
                agent_card_path="agentCard/v1.0",
            )
            card = await resolver.get_agent_card()
            if not has_v1_jsonrpc_interface(card):
                raise RuntimeError(
                    "The Agent Card does not advertise A2A v1.0 JSON-RPC."
                )
            client = await create_client(
                agent=card,
                client_config=ClientConfig(
                    streaming=False,
                    httpx_client=http_client,
                ),
            )
            try:
                await send_text(client, remember_message(marker))
                await wait_for_memory(settings, marker)
                recall = await send_text(client, recall_query(marker))
                if not has_memory_proof([recall], marker):
                    raise RuntimeError(
                        "A2A recall did not contain this run's marker and "
                        "expected preference."
                    )
            finally:
                await client.close()
    finally:
        credential.close()


def main() -> None:
    load_dotenv(override=False)
    asyncio.run(run())


if __name__ == "__main__":
    main()
