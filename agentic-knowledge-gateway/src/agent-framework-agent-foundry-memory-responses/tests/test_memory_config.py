import copy
import unittest
from types import SimpleNamespace

from gateway.memory_config import (
    MEMORY_TTL_SECONDS,
    build_memory_definition,
    memory_search_items,
    memory_store_drift,
)

SERVICE_DEFINITION = {
    "chat_model": "gpt-5.4-mini",
    "embedding_model": "text-embedding-3-small",
    "options": {
        "user_profile_enabled": True,
        "chat_summary_enabled": False,
        "procedural_memory_enabled": False,
        "default_ttl_seconds": 604800,
    },
}


def service_store(definition: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(
        as_dict=lambda: {"definition": definition}
    )


class MemoryConfigTests(unittest.TestCase):
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

    def test_captured_service_shape_has_no_drift(self) -> None:
        store = service_store(copy.deepcopy(SERVICE_DEFINITION))
        self.assertEqual(
            memory_store_drift(
                store, "gpt-5.4-mini", "text-embedding-3-small"
            ),
            [],
        )

    def test_changed_model_is_reported(self) -> None:
        definition = copy.deepcopy(SERVICE_DEFINITION)
        definition["chat_model"] = "other-model"
        drift = memory_store_drift(
            service_store(definition),
            "gpt-5.4-mini",
            "text-embedding-3-small",
        )
        self.assertTrue(
            any("definition.chat_model" in item for item in drift)
        )

    def test_changed_embedding_model_is_reported(self) -> None:
        definition = copy.deepcopy(SERVICE_DEFINITION)
        definition["embedding_model"] = "other-embedding"
        drift = memory_store_drift(
            service_store(definition),
            "gpt-5.4-mini",
            "text-embedding-3-small",
        )
        self.assertTrue(
            any("definition.embedding_model" in item for item in drift)
        )

    def test_missing_options_are_strict_drift(self) -> None:
        definition = copy.deepcopy(SERVICE_DEFINITION)
        definition.pop("options")
        drift = memory_store_drift(
            service_store(definition),
            "gpt-5.4-mini",
            "text-embedding-3-small",
        )
        self.assertTrue(
            any("options.default_ttl_seconds" in item for item in drift)
        )
        self.assertTrue(
            any("options.user_profile_enabled" in item for item in drift)
        )

    def test_missing_ttl_is_strict_drift(self) -> None:
        definition = copy.deepcopy(SERVICE_DEFINITION)
        definition["options"].pop("default_ttl_seconds")
        drift = memory_store_drift(
            service_store(definition),
            "gpt-5.4-mini",
            "text-embedding-3-small",
        )
        self.assertIn(
            "options.default_ttl_seconds: actual=None, expected=604800",
            drift,
        )

    def test_changed_ttl_is_reported(self) -> None:
        definition = copy.deepcopy(SERVICE_DEFINITION)
        definition["options"]["default_ttl_seconds"] = 3600
        drift = memory_store_drift(
            service_store(definition),
            "gpt-5.4-mini",
            "text-embedding-3-small",
        )
        self.assertIn(
            "options.default_ttl_seconds: actual=3600, expected=604800",
            drift,
        )

    def test_changed_memory_feature_is_reported(self) -> None:
        definition = copy.deepcopy(SERVICE_DEFINITION)
        definition["options"]["procedural_memory_enabled"] = True
        drift = memory_store_drift(
            service_store(definition),
            "gpt-5.4-mini",
            "text-embedding-3-small",
        )
        self.assertTrue(
            any("procedural_memory_enabled" in item for item in drift)
        )


if __name__ == "__main__":
    unittest.main()
