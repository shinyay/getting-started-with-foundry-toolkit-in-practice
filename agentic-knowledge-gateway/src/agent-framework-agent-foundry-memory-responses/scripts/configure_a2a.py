"""Enable and verify incoming A2A v1.0 on the Hosted Gateway."""

import httpx
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from gateway.a2a_config import (
    a2a_base_url,
    agent_card_url,
    build_agent_card,
    build_agent_endpoint,
    has_v1_jsonrpc_interface,
)
from gateway.settings import A2ASettings


def configure() -> None:
    settings = A2ASettings.from_env()
    gateway = settings.gateway
    credential = DefaultAzureCredential()
    project = AIProjectClient(
        endpoint=gateway.project_endpoint,
        credential=credential,
    )
    try:
        project.agents.update_details(
            agent_name=settings.agent_name,
            agent_endpoint=build_agent_endpoint(),
            agent_card=build_agent_card(),
        )
        token = credential.get_token(
            "https://ai.azure.com/.default"
        ).token
        card_url = agent_card_url(
            gateway.project_endpoint, settings.agent_name
        )
        response = httpx.get(
            card_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        response.raise_for_status()
        card = response.json()
        if not has_v1_jsonrpc_interface(card):
            raise RuntimeError(
                "Foundry did not advertise an A2A v1.0 JSON-RPC "
                "interface in the served Agent Card."
            )
        print("Incoming A2A v1.0 is enabled.")
        print(
            "A2A endpoint: "
            f"{a2a_base_url(gateway.project_endpoint, settings.agent_name)}"
        )
        print(f"Agent Card: {card_url}")
    finally:
        project.close()
        credential.close()


def main() -> None:
    load_dotenv(override=False)
    configure()


if __name__ == "__main__":
    main()
