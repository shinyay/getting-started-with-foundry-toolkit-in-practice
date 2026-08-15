"""Typed environment configuration for the Gateway and its tools."""

from __future__ import annotations

from dataclasses import dataclass
from os import environ
from typing import Mapping


def required_setting(values: Mapping[str, str], name: str) -> str:
    """Return a required setting and reject unresolved manifest placeholders."""
    value = values.get(name, "").strip()
    unresolved = (
        value.startswith("${") and value.endswith("}")
    ) or (
        value.startswith("{{") and value.endswith("}}")
    )
    if not value or unresolved:
        raise ValueError(
            f"{name} is required and must contain a resolved value."
        )
    return value


@dataclass(frozen=True)
class GatewaySettings:
    """Runtime settings shared by the model and Memory provider."""

    project_endpoint: str
    model_deployment: str
    memory_store_name: str
    memory_scope: str

    @classmethod
    def from_env(
        cls, values: Mapping[str, str] | None = None
    ) -> "GatewaySettings":
        source = environ if values is None else values
        return cls(
            project_endpoint=required_setting(
                source, "FOUNDRY_PROJECT_ENDPOINT"
            ),
            model_deployment=required_setting(
                source, "AZURE_AI_MODEL_DEPLOYMENT_NAME"
            ),
            memory_store_name=required_setting(
                source, "MEMORY_STORE_NAME"
            ),
            memory_scope=required_setting(source, "MEMORY_SCOPE"),
        )


@dataclass(frozen=True)
class ProvisioningSettings:
    """Settings used only while creating the Memory Store."""

    gateway: GatewaySettings
    embedding_model_deployment: str

    @classmethod
    def from_env(
        cls, values: Mapping[str, str] | None = None
    ) -> "ProvisioningSettings":
        source = environ if values is None else values
        return cls(
            gateway=GatewaySettings.from_env(source),
            embedding_model_deployment=required_setting(
                source, "AZURE_AI_EMBEDDING_MODEL_DEPLOYMENT_NAME"
            ),
        )


@dataclass(frozen=True)
class A2ASettings:
    """Settings used to configure and call the Hosted A2A endpoint."""

    gateway: GatewaySettings
    agent_name: str

    @classmethod
    def from_env(
        cls, values: Mapping[str, str] | None = None
    ) -> "A2ASettings":
        source = environ if values is None else values
        return cls(
            gateway=GatewaySettings.from_env(source),
            agent_name=required_setting(
                source, "FOUNDRY_HOSTED_AGENT_NAME"
            ),
        )
