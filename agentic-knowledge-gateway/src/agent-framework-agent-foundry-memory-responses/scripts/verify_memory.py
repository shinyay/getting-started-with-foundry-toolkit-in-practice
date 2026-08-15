"""Poll Foundry Memory and verify expected tutorial concepts."""

from __future__ import annotations

import argparse
import asyncio
import time

from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

from gateway.memory_config import memory_search_items
from gateway.settings import GatewaySettings
from scripts.memory_proof import (
    PREFERENCE_TERMS,
    has_memory_proof,
    proof_code,
    recall_query,
    validate_marker,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--marker",
        required=True,
        type=validate_marker,
        help="Unique synthetic marker included in the current remember request.",
    )
    parser.add_argument("--query")
    parser.add_argument(
        "--expect",
        action="append",
        dest="expected_terms",
        help="Required term. Repeat the option to require multiple terms.",
    )
    parser.add_argument("--timeout", type=int, default=300)
    return parser.parse_args()


async def verify(args: argparse.Namespace) -> None:
    settings = GatewaySettings.from_env()
    expected_terms = args.expected_terms or list(PREFERENCE_TERMS)
    query = args.query or recall_query(args.marker)
    deadline = time.monotonic() + args.timeout

    async with (
        DefaultAzureCredential() as credential,
        AIProjectClient(
            endpoint=settings.project_endpoint,
            credential=credential,
            allow_preview=True,
        ) as project,
    ):
        while time.monotonic() < deadline:
            result = await project.beta.memory_stores.search_memories(
                name=settings.memory_store_name,
                scope=settings.memory_scope,
                items=memory_search_items(query),
            )
            contents = [
                item.memory_item.content for item in result.memories
            ]
            if has_memory_proof(
                contents,
                args.marker,
                expected_terms,
            ):
                print(
                    "Verified this run's composite code in one Foundry "
                    "Memory item:"
                )
                for content in contents:
                    print(f"- {content}")
                return
            await asyncio.sleep(5)

    raise TimeoutError(
        "Foundry Memory did not return all expected terms before timeout: "
        + ", ".join([proof_code(args.marker), *expected_terms])
    )


def main() -> None:
    load_dotenv(override=False)
    asyncio.run(verify(parse_args()))


if __name__ == "__main__":
    main()
