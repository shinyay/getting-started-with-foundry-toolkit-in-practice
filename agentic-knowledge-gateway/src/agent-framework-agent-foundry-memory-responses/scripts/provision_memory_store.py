"""Create and verify the tutorial Foundry Memory Store."""

import asyncio

from azure.ai.projects.aio import AIProjectClient
from azure.core.exceptions import ResourceNotFoundError
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

from gateway.memory_config import (
    MEMORY_HEALTH_QUERY,
    build_memory_definition,
    memory_search_items,
    memory_store_drift,
)
from gateway.settings import ProvisioningSettings


async def provision() -> None:
    settings = ProvisioningSettings.from_env()
    gateway = settings.gateway
    async with (
        DefaultAzureCredential() as credential,
        AIProjectClient(
            endpoint=gateway.project_endpoint,
            credential=credential,
            allow_preview=True,
        ) as project,
    ):
        try:
            store = await project.beta.memory_stores.get(
                name=gateway.memory_store_name
            )
        except ResourceNotFoundError:
            definition = build_memory_definition(
                gateway.model_deployment,
                settings.embedding_model_deployment,
            )
            print(
                f"Creating Memory Store '{gateway.memory_store_name}'..."
            )
            await project.beta.memory_stores.create(
                name=gateway.memory_store_name,
                description=(
                    "Seven-day synthetic memory for the Agentic Knowledge "
                    "Gateway tutorial"
                ),
                definition=definition,
            )
            store = await project.beta.memory_stores.get(
                name=gateway.memory_store_name
            )

        drift = memory_store_drift(
            store,
            gateway.model_deployment,
            settings.embedding_model_deployment,
        )
        if drift:
            details = "\n  - ".join(drift)
            raise RuntimeError(
                "Existing Memory Store configuration is incompatible:\n"
                f"  - {details}\n"
                "Delete or rename the tutorial store explicitly; it will not "
                "be recreated automatically."
            )

        await project.beta.memory_stores.search_memories(
            name=gateway.memory_store_name,
            scope=gateway.memory_scope,
            items=memory_search_items(MEMORY_HEALTH_QUERY),
        )
        print(
            f"Verified Memory Store '{store.name}' and scope "
            f"'{gateway.memory_scope}'."
        )


def main() -> None:
    load_dotenv(override=False)
    asyncio.run(provision())


if __name__ == "__main__":
    main()
