#!/usr/bin/env python3
"""Create or update the demo chat agent that delegates to the Gateway.

The chat agent holds no knowledge of its own. It reaches the Agentic Knowledge
Gateway through an incoming A2A v1.0 connection, so every factual answer has to
come from Foundry Memory behind the Gateway.

The Foundry Toolkit user interface currently hides A2A connections from the
Prompt Agent tool picker, so this script configures the agent through the
Foundry data plane instead.
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from gateway.settings import GatewaySettings

API_VERSION = "v1"
FOUNDRY_SCOPE = "https://ai.azure.com/.default"

INSTRUCTIONS = """
You are a chat assistant for a fictional engineering team. You have no
knowledge of your own about this team, its projects, decisions, environments,
schedules, naming conventions, or people.

The Agentic Knowledge Gateway tool is your only source for that knowledge.

Rules you must follow:

1. If a question touches the team, a project, an identifier scheme, an
   architecture decision, an environment, a schedule, an approval process, a
   nickname, or anything the user says was remembered, call the Gateway tool
   immediately in the same turn, before you write any answer.
2. Send the user's question to the Gateway in the user's own words. Do not
   shorten it, translate it, or replace its nouns with your own summary,
   because the Gateway searches its memory using the text you send.
3. Never offer to check, never ask for permission, and never say that you
   could query the Gateway. Call it instead.
4. If the Gateway reports no record, call it one more time using the key
   nouns from the question, then answer from that second result.
5. The Gateway may reply with structured data. Read only the human readable
   text inside it and never show raw JSON or protocol envelopes to the user.
6. Build your answer only from what the Gateway returns. Reproduce specific
   values such as identifiers, times, names, and record numbers exactly.
7. If the Gateway still has nothing relevant, state plainly that the Gateway
   has no record of it. Never guess, infer, or fill the gap from general
   knowledge.
8. Keep answers short, concrete, and in the user's language.
""".strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--chat-agent-name",
        default=os.environ.get("DEMO_CHAT_AGENT_NAME", "knowledge-chat-agent"),
        help="Prompt Agent to create or update.",
    )
    parser.add_argument(
        "--connection-name",
        default=os.environ.get("DEMO_A2A_CONNECTION_NAME", "gateway-a2a"),
        help="RemoteA2A project connection that targets the Gateway.",
    )
    return parser.parse_args()


def find_connection(client: httpx.Client, endpoint: str, name: str) -> dict:
    response = client.get(
        f"{endpoint}/connections?api-version={API_VERSION}"
    )
    response.raise_for_status()
    for connection in response.json().get("value", []):
        if connection.get("name") != name:
            continue
        if connection.get("type") != "RemoteA2A":
            raise RuntimeError(
                f"Connection '{name}' is not a RemoteA2A connection."
            )
        if connection.get("metadata", {}).get("AgentCardPath"):
            raise RuntimeError(
                f"Connection '{name}' sets AgentCardPath. Foundry agents must "
                "use the default agent card path; recreate the connection "
                "without that metadata."
            )
        return connection
    raise RuntimeError(
        f"Connection '{name}' was not found in this project. Create it with "
        "'azd ai connection create' before running this script."
    )


def main() -> int:
    load_dotenv(override=False)
    args = parse_args()
    settings = GatewaySettings.from_env()
    endpoint = settings.project_endpoint.rstrip("/")

    credential = DefaultAzureCredential()
    try:
        token = credential.get_token(FOUNDRY_SCOPE).token
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=120.0, headers=headers) as client:
            connection = find_connection(
                client, endpoint, args.connection_name
            )
            body = {
                "definition": {
                    "kind": "prompt",
                    "model": settings.model_deployment,
                    "instructions": INSTRUCTIONS,
                    "tools": [
                        {
                            "type": "a2a_preview",
                            "project_connection_id": connection["id"],
                        }
                    ],
                }
            }
            response = client.post(
                f"{endpoint}/agents/{args.chat_agent_name}"
                f"/versions?api-version={API_VERSION}",
                json=body,
            )
            if response.status_code not in (200, 201):
                print(
                    "Failed to publish the chat agent version: "
                    f"HTTP {response.status_code}"
                )
                print(response.text[:500])
                return 1
            payload = response.json()
    finally:
        credential.close()

    print(
        f"Published '{args.chat_agent_name}' version {payload['version']} "
        f"({payload['status']}) with the Gateway A2A tool."
    )
    print(
        "Select this version in the Foundry Toolkit Prompt Agent playground "
        "before running the demo."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
