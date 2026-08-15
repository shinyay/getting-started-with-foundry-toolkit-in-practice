"""Create and verify run-specific synthetic Memory proof markers."""

from __future__ import annotations

import re
from collections.abc import Iterable
from uuid import uuid4

from gateway.memory_config import contains_all_terms

PREFERENCE_TERMS = ("bullet", "concise")
MARKER_PATTERN = re.compile(r"^akg[0-9a-f]{16}$")


def create_marker() -> str:
    """Return a synthetic marker that is unique to one verification run."""
    return f"akg{uuid4().hex[:16]}"


def validate_marker(value: str) -> str:
    """Reject values that are not tutorial-generated synthetic markers."""
    marker = value.strip().lower()
    if not MARKER_PATTERN.fullmatch(marker):
        raise ValueError(
            "marker must use the format 'akg' followed by 16 hexadecimal "
            "characters"
        )
    return marker


def proof_code(marker: str) -> str:
    """Bind the unique run marker and preference semantics in one value."""
    return f"{validate_marker(marker)}-concise-bullets"


def remember_message(marker: str) -> str:
    """Build the synthetic fact written during the current proof run."""
    code = proof_code(marker)
    return (
        "Remember this exact synthetic tutorial formatting preference code: "
        f"{code}. Preserve the full code exactly. "
        "It means I prefer concise answers in bullet points."
    )


def recall_query(marker: str) -> str:
    """Build a query that targets the current proof run."""
    code = proof_code(marker)
    return (
        "What does the synthetic tutorial formatting preference code "
        f"{code} mean? Include the full code exactly in your answer."
    )


def has_memory_proof(
    values: Iterable[str],
    marker: str,
    terms: Iterable[str] = PREFERENCE_TERMS,
) -> bool:
    """Require one item to contain this run's code and expected concepts."""
    required = (proof_code(marker), *terms)
    return any(contains_all_terms([value], required) for value in values)
