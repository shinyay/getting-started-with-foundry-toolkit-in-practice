"""Verify a run-specific synthetic key/value pair through Foundry Memory."""

from __future__ import annotations

import argparse
import asyncio

from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

from gateway.settings import GatewaySettings
from scripts.memory_polling import (
    list_memory_contents_with_retry,
    wait_for_memory_proof,
)
from scripts.memory_proof import (
    MemoryProof,
    has_memory_proof,
    validate_key,
    validate_value,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--key",
        required=True,
        type=validate_key,
        help="Unique synthetic key included in the current remember request.",
    )
    parser.add_argument(
        "--value",
        required=True,
        type=validate_value,
        help="Independent synthetic value associated with the key.",
    )
    parser.add_argument(
        "--expect-absent",
        action="store_true",
        help="Fail if the exact pair already exists; use before the write.",
    )
    parser.add_argument("--timeout", type=int, default=300)
    return parser.parse_args()


async def verify(args: argparse.Namespace) -> None:
    settings = GatewaySettings.from_env()
    proof = MemoryProof(args.key, args.value)

    async with (
        DefaultAzureCredential() as credential,
        AIProjectClient(
            endpoint=settings.project_endpoint,
            credential=credential,
            allow_preview=True,
        ) as project,
    ):
        if args.expect_absent:
            contents = await list_memory_contents_with_retry(
                project,
                settings,
                timeout=args.timeout,
            )
            if has_memory_proof(contents, proof):
                raise RuntimeError(
                    "The generated key/value pair already exists in Foundry "
                    f"Memory: {proof.pair}"
                )
            print("Verified the generated key/value pair is absent.")
            return

        contents = await wait_for_memory_proof(
            project,
            settings,
            proof,
            timeout=args.timeout,
        )
        print(
            "Verified this run's exact key/value pair in one Foundry "
            "Memory item:"
        )
        for content in contents:
            print(f"- {content}")


def main() -> None:
    load_dotenv(override=False)
    asyncio.run(verify(parse_args()))


if __name__ == "__main__":
    main()
