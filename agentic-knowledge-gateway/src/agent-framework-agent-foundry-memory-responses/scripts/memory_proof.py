"""Compatibility exports for the runtime-safe proof contract."""

from gateway.memory_proof import (
    MemoryProof,
    create_proof,
    has_memory_proof,
    has_recalled_value,
    recall_query,
    remember_message,
    validate_key,
    validate_value,
)

__all__ = [
    "MemoryProof",
    "create_proof",
    "has_memory_proof",
    "has_recalled_value",
    "recall_query",
    "remember_message",
    "validate_key",
    "validate_value",
]
