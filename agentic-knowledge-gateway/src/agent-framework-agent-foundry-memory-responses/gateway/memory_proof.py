"""Create and verify run-specific synthetic Memory key/value proofs."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from uuid import uuid4

KEY_PATTERN = re.compile(r"^akg[0-9a-f]{16}$")
VALUE_PATTERN = re.compile(r"^akv[0-9a-f]{16}$")
PAIR_PATTERN = re.compile(
    r"(?<![0-9a-z])akg[0-9a-f]{16}=akv[0-9a-f]{16}(?![0-9a-z])",
    re.IGNORECASE,
)


def validate_key(value: str) -> str:
    """Reject values that are not tutorial-generated synthetic keys."""
    key = value.strip().lower()
    if not KEY_PATTERN.fullmatch(key):
        raise ValueError(
            "key must use the format 'akg' followed by 16 hexadecimal "
            "characters"
        )
    return key


def validate_value(value: str) -> str:
    """Reject values that are not tutorial-generated synthetic values."""
    proof_value = value.strip().lower()
    if not VALUE_PATTERN.fullmatch(proof_value):
        raise ValueError(
            "value must use the format 'akv' followed by 16 hexadecimal "
            "characters"
        )
    return proof_value


@dataclass(frozen=True)
class MemoryProof:
    """An independently random key/value association for one proof run."""

    key: str
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", validate_key(self.key))
        object.__setattr__(self, "value", validate_value(self.value))

    @property
    def pair(self) -> str:
        return f"{self.key}={self.value}"


def create_proof() -> MemoryProof:
    """Return a proof whose value cannot be inferred from its key."""
    return MemoryProof(
        key=f"akg{uuid4().hex[:16]}",
        value=f"akv{uuid4().hex[:16]}",
    )


def contains_memory_proof_pair(text: str) -> bool:
    """Return whether text contains one complete synthetic proof pair."""
    return PAIR_PATTERN.search(text) is not None


def remember_message(proof: MemoryProof) -> str:
    """Build the synthetic fact written during the current proof run."""
    return (
        "Remember this exact synthetic tutorial key/value association as one "
        f"fact: {proof.pair}. Preserve the complete pair exactly."
    )


def recall_query(key: str) -> str:
    """Ask for a value without exposing it in the query."""
    key = validate_key(key)
    return (
        "What exact synthetic tutorial value is associated with key "
        f"{key}? Return the value exactly."
    )


def has_memory_proof(
    values: Iterable[str],
    proof: MemoryProof,
) -> bool:
    """Require the exact key/value pair in one authoritative Memory item."""
    expected = proof.pair.lower()
    return any(expected in value.lower() for value in values)


def has_recalled_value(text: str, proof: MemoryProof) -> bool:
    """Require the independently generated value in fresh recall output."""
    return proof.value.lower() in text.lower()
