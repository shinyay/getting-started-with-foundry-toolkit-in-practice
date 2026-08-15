"""Current Foundry incoming A2A v1.0 configuration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

from azure.ai.projects.models import (
    A2AProtocolConfiguration,
    AgentCard,
    AgentCardSkill,
    AgentEndpointConfig,
    ProtocolConfiguration,
    ResponsesProtocolConfiguration,
)


def build_agent_card() -> AgentCard:
    """Describe the constrained tutorial knowledge-memory capability."""
    return AgentCard(
        version="1.0",
        description=(
            "A tutorial Agentic Knowledge Gateway that stores and recalls "
            "synthetic, non-sensitive facts in one shared tutorial scope."
        ),
        skills=[
            AgentCardSkill(
                id="tutorial-knowledge-memory",
                name="Tutorial knowledge memory",
                description=(
                    "Remembers and recalls synthetic tutorial preferences "
                    "and project facts across separate tasks."
                ),
            )
        ],
    )


def build_agent_endpoint() -> AgentEndpointConfig:
    """Enable both Responses and incoming A2A on the Hosted Agent."""
    return AgentEndpointConfig(
        protocol_configuration=ProtocolConfiguration(
            responses=ResponsesProtocolConfiguration(),
            a2a=A2AProtocolConfiguration(),
        )
    )


def a2a_base_url(project_endpoint: str, agent_name: str) -> str:
    """Return the authenticated incoming A2A base URL."""
    endpoint = project_endpoint.rstrip("/")
    encoded_name = quote(agent_name, safe="")
    return (
        f"{endpoint}/agents/{encoded_name}/endpoint/protocols/a2a"
    )


def agent_card_url(project_endpoint: str, agent_name: str) -> str:
    """Return the explicit v1.0 Agent Card discovery URL."""
    return f"{a2a_base_url(project_endpoint, agent_name)}/agentCard/v1.0"


def has_v1_jsonrpc_interface(card: Any) -> bool:
    """Return whether a served Agent Card advertises A2A v1.0 JSON-RPC."""
    interfaces = (
        card.get("supportedInterfaces", [])
        if isinstance(card, Mapping)
        else getattr(card, "supported_interfaces", [])
    )
    for interface in interfaces:
        if isinstance(interface, Mapping):
            version = interface.get("protocolVersion")
            binding = interface.get("protocolBinding")
        else:
            version = getattr(interface, "protocol_version", None)
            binding = getattr(interface, "protocol_binding", None)
        if version == "1.0" and binding == "JSONRPC":
            return True
    return False
