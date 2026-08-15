import unittest

from scripts.memory_proof import (
    create_marker,
    has_memory_proof,
    proof_code,
    recall_query,
    remember_message,
    validate_marker,
)

MARKER = "akg0123456789abcdef"
OTHER_MARKER = MARKER.replace("0", "1", 1)


class MemoryProofTests(unittest.TestCase):
    def test_proof_code_in_one_item_passes(self) -> None:
        self.assertTrue(
            has_memory_proof(
                [
                    "The exact preference code is "
                    f"{proof_code(MARKER)}.",
                ],
                MARKER,
            )
        )

    def test_custom_term_must_share_the_proof_item(self) -> None:
        self.assertFalse(
            has_memory_proof(
                [f"The exact preference code is {proof_code(MARKER)}."],
                MARKER,
                ("brief",),
            )
        )

    def test_stale_concepts_cannot_combine_with_marker(self) -> None:
        self.assertFalse(
            has_memory_proof(
                [
                    "The user prefers concise answers.",
                    "Use bullet-point formatting.",
                    f"Marker: {MARKER}",
                ],
                MARKER,
            )
        )

    def test_preference_rejects_another_runs_code(self) -> None:
        self.assertFalse(
            has_memory_proof(
                [f"Preference code: {proof_code(OTHER_MARKER)}"],
                MARKER,
            )
        )

    def test_generated_marker_is_valid(self) -> None:
        marker = create_marker()
        self.assertEqual(validate_marker(marker), marker)

    def test_messages_include_the_full_proof_code(self) -> None:
        code = proof_code(MARKER)
        self.assertIn(code, remember_message(MARKER))
        self.assertIn(code, recall_query(MARKER))


if __name__ == "__main__":
    unittest.main()
