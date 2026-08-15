"""Explicitly delete tutorial Memory scope data or the entire store."""

import argparse
import asyncio

from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

from gateway.settings import GatewaySettings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--scope",
        action="store_true",
        help="Delete all items in the configured tutorial scope.",
    )
    target.add_argument(
        "--store",
        action="store_true",
        help="Delete the entire tutorial Memory Store.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm the irreversible deletion without prompting.",
    )
    return parser.parse_args()


async def cleanup(args: argparse.Namespace) -> None:
    settings = GatewaySettings.from_env()
    target = (
        f"scope '{settings.memory_scope}'"
        if args.scope
        else f"store '{settings.memory_store_name}'"
    )
    if not args.yes:
        confirmation = input(f"Delete {target}? Type DELETE to continue: ")
        if confirmation != "DELETE":
            raise SystemExit("Deletion cancelled.")

    async with (
        DefaultAzureCredential() as credential,
        AIProjectClient(
            endpoint=settings.project_endpoint,
            credential=credential,
            allow_preview=True,
        ) as project,
    ):
        if args.scope:
            await project.beta.memory_stores.delete_scope(
                name=settings.memory_store_name,
                scope=settings.memory_scope,
            )
        else:
            await project.beta.memory_stores.delete(
                settings.memory_store_name
            )
    print(f"Deleted {target}.")


def main() -> None:
    load_dotenv(override=False)
    asyncio.run(cleanup(parse_args()))


if __name__ == "__main__":
    main()
