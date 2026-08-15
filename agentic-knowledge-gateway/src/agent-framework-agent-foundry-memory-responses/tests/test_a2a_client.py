import unittest

from scripts.a2a_client import response_text_from_payload
from scripts.memory_proof import (
    MemoryProof,
    create_proof,
    has_memory_proof,
    has_recalled_value,
    recall_query,
    remember_message,
    validate_key,
    validate_value,
)

KEY = "akg0123456789abcdef"
VALUE = "akvfedcba9876543210"
OTHER_VALUE = "akv1111111111111111"
PROOF = MemoryProof(KEY, VALUE)


class MemoryProofTests(unittest.TestCase):
    def test_generated_key_and_value_are_valid_and_independent(self) -> None:
        proof = create_proof()
        self.assertEqual(validate_key(proof.key), proof.key)
        self.assertEqual(validate_value(proof.value), proof.value)
        self.assertNotEqual(proof.key[3:], proof.value[3:])

    def test_recall_query_does_not_expose_value(self) -> None:
        query = recall_query(PROOF.key)
        self.assertIn(PROOF.key, query)
        self.assertNotIn(PROOF.value, query)

    def test_remember_message_contains_exact_pair(self) -> None:
        self.assertIn(PROOF.pair, remember_message(PROOF))

    def test_exact_pair_in_one_item_passes(self) -> None:
        self.assertTrue(
            has_memory_proof(
                [f"The exact synthetic pair is {PROOF.pair}."],
                PROOF,
            )
        )

    def test_split_key_and_value_cannot_pass(self) -> None:
        self.assertFalse(
            has_memory_proof(
                [f"Key: {PROOF.key}", f"Value: {PROOF.value}"],
                PROOF,
            )
        )

    def test_wrong_value_cannot_pass(self) -> None:
        self.assertFalse(
            has_memory_proof(
                [f"Pair: {PROOF.key}={OTHER_VALUE}"],
                PROOF,
            )
        )

    def test_fresh_recall_requires_independent_value(self) -> None:
        self.assertTrue(has_recalled_value(f"Value: {PROOF.value}", PROOF))
        self.assertFalse(
            has_recalled_value(f"Value: {OTHER_VALUE}", PROOF)
        )


class A2AResponseTests(unittest.TestCase):
    def test_extracts_artifact_text(self) -> None:
        payload = {
            "task": {
                "artifacts": [
                    {"parts": [{"text": "artifact output"}]}
                ]
            }
        }
        self.assertEqual(
            response_text_from_payload(payload),
            "artifact output",
        )

    def test_extracts_task_status_message_text(self) -> None:
        payload = {
            "task": {
                "status": {
                    "message": {
                        "parts": [{"text": "status output"}]
                    }
                }
            }
        }
        self.assertEqual(
            response_text_from_payload(payload),
            "status output",
        )

    def test_extracts_top_level_message_text(self) -> None:
        payload = {"message": {"parts": [{"text": "message output"}]}}
        self.assertEqual(
            response_text_from_payload(payload),
            "message output",
        )

    def test_deduplicates_text_across_channels(self) -> None:
        payload = {
            "task": {
                "artifacts": [{"parts": [{"text": "same output"}]}],
                "status": {
                    "message": {"parts": [{"text": "same output"}]}
                },
            },
            "message": {"parts": [{"text": "same output"}]},
        }
        self.assertEqual(
            response_text_from_payload(payload),
            "same output",
        )

    def test_empty_response_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "no text output"):
            response_text_from_payload({"task": {}})


if __name__ == "__main__":
    unittest.main()
