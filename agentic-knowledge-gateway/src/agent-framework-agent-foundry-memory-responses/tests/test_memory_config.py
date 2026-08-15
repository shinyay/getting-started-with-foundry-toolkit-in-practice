import unittest
from types import SimpleNamespace

from gateway.memory_config import (
    MEMORY_TTL_SECONDS,
    build_memory_definition,
    contains_all_terms,
    memory_search_items,
    memory_store_drift,
)


class MemoryConfigTests(unittest.TestCase):
    def test_term_matching_spans_normalized_memory_items(self) -> None:
        self.assertTrue(
            contains_all_terms(
                ["Prefers concise answers.", "Use bullet-point formatting."],
                ["concise", "bullet"],
            )
        )

    def test_memory_search_uses_responses_message_shape(self) -> None:
        self.assertEqual(
            memory_search_items("test query"),
            [
                {
                    "type": "message",
                    "role": "user",
                    "content": "test query",
                }
            ],
        )

    def test_definition_is_narrow_and_has_seven_day_ttl(self) -> None:
        definition = build_memory_definition(
            "gpt-5.4-mini", "text-embedding-3-small"
        ).as_dict()
        options = definition["options"]
        self.assertTrue(options["user_profile_enabled"])
        self.assertFalse(options["chat_summary_enabled"])
        self.assertFalse(options["procedural_memory_enabled"])
        self.assertEqual(
            options["default_ttl_seconds"], MEMORY_TTL_SECONDS
        )

    def test_matching_store_has_no_drift(self) -> None:
        definition = build_memory_definition(
            "gpt-5.4-mini", "text-embedding-3-small"
        ).as_dict()
        store = SimpleNamespace(
            as_dict=lambda: {"definition": definition}
        )
        self.assertEqual(
            memory_store_drift(
                store, "gpt-5.4-mini", "text-embedding-3-small"
            ),
            [],
        )

    def test_drift_is_reported_without_mutation(self) -> None:
        definition = build_memory_definition(
            "other-model", "text-embedding-3-small"
        ).as_dict()
        store = SimpleNamespace(
            as_dict=lambda: {"definition": definition}
        )
        drift = memory_store_drift(
            store, "gpt-5.4-mini", "text-embedding-3-small"
        )
        self.assertTrue(
            any("definition.chat_model" in item for item in drift)
        )


if __name__ == "__main__":
    unittest.main()
