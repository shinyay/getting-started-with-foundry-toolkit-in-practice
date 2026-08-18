#!/usr/bin/env python3
"""List the current contents of the configured tutorial Memory scope."""

from __future__ import annotations

import asyncio
import sys

from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

from gateway.settings import GatewaySettings
from scripts.memory_polling import list_memory_contents_with_retry


async def show(timeout: float) -> int:
    settings = GatewaySettings.from_env()
    async with (
        DefaultAzureCredential() as credential,
        AIProjectClient(
            endpoint=settings.project_endpoint,
            credential=credential,
            allow_preview=True,
        ) as project,
    ):
        contents = await list_memory_contents_with_retry(
            project, settings, timeout=timeout
        )

    print(f"scope '{settings.memory_scope}' holds {len(contents)} item(s).")
    for index, content in enumerate(contents, start=1):
        print(f"{index:>3}. {content}")
    return 0


def main() -> int:
    load_dotenv(override=False)
    return asyncio.run(show(timeout=120))


if __name__ == "__main__":
    sys.exit(main())
