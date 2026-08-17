"""Run the tutorial remember/recall flow through incoming A2A v1.0."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import new_text_message
from a2a.types.a2a_pb2 import Role, SendMessageRequest
from a2a.utils.errors import InternalError
from azure.ai.projects.aio import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.identity.aio import DefaultAzureCredential as AsyncCredential
from dotenv import load_dotenv
from google.protobuf.json_format import MessageToDict

from gateway.a2a_config import a2a_base_url, has_v1_jsonrpc_interface
from gateway.settings import A2ASettings
from scripts.memory_polling import (
    list_memory_contents_with_retry,
    wait_for_memory_proof,
)
from scripts.memory_proof import (
    MemoryProof,
    create_proof,
    has_memory_proof,
    has_recalled_value,
    recall_query,
    remember_message,
)

MEMORY_POLL_TIMEOUT_SECONDS = 300


def _message_texts(message: Mapping[str, Any] | None) -> list[str]:
    if not message:
        return []
    return [
        str(part["text"])
        for part in message.get("parts", [])
        if part.get("text")
    ]


def response_text_from_payload(payload: Mapping[str, Any]) -> str:
    """Extract unique text from every A2A v1.0 response channel."""
    task = payload.get("task", {})
    texts: list[str] = []
    for artifact in task.get("artifacts", []):
        texts.extend(_message_texts(artifact))
    texts.extend(_message_texts(task.get("status", {}).get("message")))
    texts.extend(_message_texts(payload.get("message")))

    unique_texts = list(dict.fromkeys(texts))
    if not unique_texts:
        raise RuntimeError("The A2A response contained no text output.")
    return "\n".join(unique_texts)


def response_text(response: Any) -> str:
    """Extract text from an A2A protobuf response."""
    payload = MessageToDict(response, preserving_proto_field_name=True)
    return response_text_from_payload(payload)


async def send_text(
    client: Any,
    text: str,
    *,
    internal_error_retries: int = 0,
    retry_delay: float = 2.0,
) -> str:
    """Send a new A2A task with bounded retry before any output arrives."""
    if internal_error_retries < 0:
        raise ValueError("internal_error_retries must be zero or greater")

    for attempt in range(internal_error_retries + 1):
        message = new_text_message(text, role=Role.ROLE_USER)
        request = SendMessageRequest(message=message)
        chunks: list[str] = []
        try:
            async for response in client.send_message(request):
                rendered = response_text(response)
                chunks.append(rendered)
                print(rendered, flush=True)
            return "\n".join(chunks)
        except InternalError:
            if chunks or attempt >= internal_error_retries:
                raise
            print(
                "A2A returned a transient internal error before output; "
                "retrying with a new task.",
                flush=True,
            )
            await asyncio.sleep(retry_delay)

    raise AssertionError("A2A retry loop completed without a result")


def require_remember_acknowledgement(
    text: str,
    proof: MemoryProof,
) -> None:
    """Fail before polling when A2A did not acknowledge the exact pair."""
    if not has_memory_proof([text], proof):
        raise RuntimeError(
            "A2A remember response did not acknowledge this run's exact "
            "synthetic pair; authoritative Memory polling was not started."
        )


async def run() -> None:
    settings = A2ASettings.from_env()
    gateway = settings.gateway
    proof = create_proof()
    print(f"Verification key: {proof.key}")
    print(f"Expected value: {proof.value}")
    base_url = a2a_base_url(
        gateway.project_endpoint, settings.agent_name
    )

    async with (
        AsyncCredential() as memory_credential,
        AIProjectClient(
            endpoint=gateway.project_endpoint,
            credential=memory_credential,
            allow_preview=True,
        ) as project,
    ):
        existing = await list_memory_contents_with_retry(
            project,
            gateway,
            timeout=60,
        )
        if has_memory_proof(existing, proof):
            raise RuntimeError(
                "The generated key/value pair unexpectedly already exists."
            )
        print("Verified the generated key/value pair is absent.")

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
                    acknowledgement = await send_text(
                        client,
                        remember_message(proof),
                    )
                    require_remember_acknowledgement(
                        acknowledgement,
                        proof,
                    )
                    contents = await wait_for_memory_proof(
                        project,
                        gateway,
                        proof,
                        timeout=MEMORY_POLL_TIMEOUT_SECONDS,
                    )
                    print(
                        "Verified this run's exact pair in one Foundry "
                        "Memory item."
                    )
                    for content in contents:
                        print(f"- {content}")
                    recall = await send_text(
                        client,
                        recall_query(proof.key),
                        internal_error_retries=1,
                    )
                    if not has_recalled_value(recall, proof):
                        raise RuntimeError(
                            "A2A fresh-task recall did not contain this run's "
                            "independent value."
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
