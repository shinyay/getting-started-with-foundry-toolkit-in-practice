"""Generate local Foundry agent metadata from the selected azd environment."""

from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

SOURCE_ROOT = Path(__file__).resolve().parents[1]
METADATA_DIR = SOURCE_ROOT / ".foundry"
TEMPLATE_PATH = METADATA_DIR / "agent-metadata.example.yaml"
OUTPUT_PATH = METADATA_DIR / "agent-metadata.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", default="dev")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Write without an interactive confirmation.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit nonzero instead of updating stale or missing metadata.",
    )
    return parser.parse_args()


def find_project_root(start: Path = SOURCE_ROOT) -> Path:
    """Find the nearest parent containing the azd manifest."""
    for candidate in (start, *start.parents):
        if (candidate / "azure.yaml").is_file():
            return candidate
    raise FileNotFoundError("Could not find azure.yaml above the agent source.")


def load_azd_values(
    project_root: Path,
    environment: str,
) -> dict[str, str]:
    """Read resolved azd state without parsing shell assignment output."""
    completed = subprocess.run(
        [
            "azd",
            "env",
            "get-values",
            "-e",
            environment,
            "--output",
            "json",
        ],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )
    values = json.loads(completed.stdout)
    if not isinstance(values, dict):
        raise ValueError("azd env get-values did not return a JSON object.")
    return {
        str(name): str(value)
        for name, value in values.items()
        if value is not None
    }


def required_value(
    values: Mapping[str, str],
    *names: str,
) -> str:
    """Resolve the first populated azd value from an explicit name list."""
    for name in names:
        value = values.get(name, "").strip()
        if value:
            return value
    raise ValueError(
        "Missing required azd environment value; expected one of: "
        + ", ".join(names)
    )


def agent_environment_prefix(agent_name: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]", "_", agent_name).upper()
    return f"AGENT_{normalized}"


def build_metadata(
    template: Mapping[str, Any],
    values: Mapping[str, str],
    environment: str,
) -> dict[str, Any]:
    """Merge dynamic azd values without discarding cached test cases."""
    metadata = copy.deepcopy(dict(template))
    environments = metadata.get("environments")
    if not isinstance(environments, dict) or not environments:
        raise ValueError("Metadata example must define at least one environment.")

    base_name = str(metadata.get("defaultEnvironment", "")).strip()
    base = environments.get(environment) or environments.get(base_name)
    if not isinstance(base, dict):
        raise ValueError(
            "Metadata example does not contain a reusable environment entry."
        )

    agent_name = required_value(
        values,
        "FOUNDRY_HOSTED_AGENT_NAME",
    )
    prefix = agent_environment_prefix(agent_name)
    selected = copy.deepcopy(base)
    selected.update(
        {
            "projectEndpoint": required_value(
                values,
                f"{prefix}_PROJECT_ENDPOINT",
                "FOUNDRY_PROJECT_ENDPOINT",
                "AZURE_AI_PROJECT_CONNECTIONS_PROJECT_ENDPOINT",
            ),
            "agentName": agent_name,
            "agentVersion": required_value(
                values,
                f"{prefix}_VERSION",
            ),
            "region": required_value(values, "AZURE_LOCATION"),
        }
    )
    selected["memory"] = {
        "storeName": required_value(values, "MEMORY_STORE_NAME"),
        "scope": required_value(values, "MEMORY_SCOPE"),
        "defaultTtlSeconds": 604800,
    }
    selected["models"] = {
        "chatDeployment": required_value(
            values,
            "AZURE_AI_MODEL_DEPLOYMENT_NAME",
        ),
        "embeddingDeployment": required_value(
            values,
            "AZURE_AI_EMBEDDING_MODEL_DEPLOYMENT_NAME",
        ),
    }

    metadata["defaultEnvironment"] = environment
    metadata["environments"] = copy.deepcopy(environments)
    metadata["environments"][environment] = selected
    return metadata


def render_metadata(metadata: Mapping[str, Any]) -> str:
    return yaml.safe_dump(
        dict(metadata),
        sort_keys=False,
        allow_unicode=False,
    )


def write_metadata_atomic(path: Path, content: str) -> None:
    """Replace generated metadata without exposing a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)


def metadata_summary(
    metadata: Mapping[str, Any],
    environment: str,
) -> str:
    selected = metadata["environments"][environment]
    return "\n".join(
        [
            f"Environment: {environment}",
            f"Project endpoint: {selected['projectEndpoint']}",
            f"Agent: {selected['agentName']} version {selected['agentVersion']}",
            f"Region: {selected['region']}",
            f"Memory Store: {selected['memory']['storeName']}",
            f"Memory scope: {selected['memory']['scope']}",
        ]
    )


def run(args: argparse.Namespace) -> int:
    template = yaml.safe_load(TEMPLATE_PATH.read_text(encoding="utf-8"))
    values = load_azd_values(find_project_root(), args.environment)
    metadata = build_metadata(template, values, args.environment)
    content = render_metadata(metadata)

    print(metadata_summary(metadata, args.environment))
    current = (
        OUTPUT_PATH.read_text(encoding="utf-8")
        if OUTPUT_PATH.is_file()
        else None
    )
    if current == content:
        print(f"Metadata is current: {OUTPUT_PATH}")
        return 0

    if args.check:
        print(f"Metadata is missing or stale: {OUTPUT_PATH}")
        return 1

    if not args.yes:
        confirmation = input(
            "Type WRITE to generate local Foundry metadata: "
        )
        if confirmation != "WRITE":
            print("Metadata was not changed.")
            return 1

    write_metadata_atomic(OUTPUT_PATH, content)
    print(f"Generated local Foundry metadata: {OUTPUT_PATH}")
    return 0


def main() -> None:
    raise SystemExit(run(parse_args()))


if __name__ == "__main__":
    main()
