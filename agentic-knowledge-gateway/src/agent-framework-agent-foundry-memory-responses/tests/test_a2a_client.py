import unittest
from unittest.mock import AsyncMock, patch

from a2a.utils.errors import InternalError

from scripts.a2a_client import (
    acknowledges_memory_proof,
    prove_remembered_pair,
    response_text_from_payload,
    send_text,
)
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

    def test_refusal_is_not_treated_as_acknowledgement(self) -> None:
        self.assertFalse(
            acknowledges_memory_proof("I cannot store that.", PROOF)
        )

    def test_exact_remember_acknowledgement_is_detected(self) -> None:
        self.assertTrue(
            acknowledges_memory_proof(
                f"Stored exact synthetic association: {PROOF.pair}",
                PROOF,
            )
        )


class RememberProofTests(unittest.IsolatedAsyncioTestCase):
    async def test_unacknowledged_write_passes_when_memory_holds_pair(
        self,
    ) -> None:
        with patch(
            "scripts.a2a_client.wait_for_memory_proof",
            new=AsyncMock(return_value=[PROOF.pair]),
        ) as wait:
            contents = await prove_remembered_pair(
                object(),
                object(),
                PROOF,
                "Done. I stored the association.",
            )

        self.assertEqual(contents, [PROOF.pair])
        self.assertEqual(wait.await_args.kwargs["timeout"], 120)

    async def test_acknowledged_write_uses_the_full_poll_budget(self) -> None:
        with patch(
            "scripts.a2a_client.wait_for_memory_proof",
            new=AsyncMock(return_value=[PROOF.pair]),
        ) as wait:
            await prove_remembered_pair(
                object(),
                object(),
                PROOF,
                f"Stored exact synthetic association: {PROOF.pair}",
            )

        self.assertEqual(wait.await_args.kwargs["timeout"], 300)

    async def test_unacknowledged_write_reports_missing_tool_call(
        self,
    ) -> None:
        with (
            patch(
                "scripts.a2a_client.wait_for_memory_proof",
                new=AsyncMock(side_effect=TimeoutError("not visible")),
            ),
            self.assertRaisesRegex(
                RuntimeError,
                "strict write-through tool call",
            ),
        ):
            await prove_remembered_pair(
                object(),
                object(),
                PROOF,
                "I cannot store that.",
            )

    async def test_acknowledged_timeout_keeps_the_original_error(
        self,
    ) -> None:
        with (
            patch(
                "scripts.a2a_client.wait_for_memory_proof",
                new=AsyncMock(side_effect=TimeoutError("not visible")),
            ),
            self.assertRaises(TimeoutError),
        ):
            await prove_remembered_pair(
                object(),
                object(),
                PROOF,
                f"Stored exact synthetic association: {PROOF.pair}",
            )


class FakeA2AClient:
    def __init__(self, outcomes: list[list[object] | BaseException]) -> None:
        self.outcomes = outcomes
        self.calls = 0

    def send_message(self, _: object):
        outcome = self.outcomes[self.calls]
        self.calls += 1

        async def responses():
            if isinstance(outcome, BaseException):
                raise outcome
            for response in outcome:
                yield response

        return responses()


class A2ARetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_read_only_retry_uses_a_new_task(self) -> None:
        client = FakeA2AClient([InternalError(), [object()]])
        with (
            patch(
                "scripts.a2a_client.response_text",
                return_value="recalled",
            ),
            patch(
                "scripts.a2a_client.asyncio.sleep",
                new=AsyncMock(),
            ) as sleep,
        ):
            result = await send_text(
                client,
                "recall",
                internal_error_retries=1,
            )
        self.assertEqual(result, "recalled")
        self.assertEqual(client.calls, 2)
        sleep.assert_awaited_once()

    async def test_partial_output_is_never_retried(self) -> None:
        class PartialThenErrorClient:
            def __init__(self) -> None:
                self.calls = 0

            def send_message(self, _: object):
                self.calls += 1

                async def responses():
                    yield object()
                    raise InternalError()

                return responses()

        client = PartialThenErrorClient()
        with (
            patch(
                "scripts.a2a_client.response_text",
                return_value="partial",
            ),
            self.assertRaises(InternalError),
        ):
            await send_text(
                client,
                "recall",
                internal_error_retries=1,
            )
        self.assertEqual(client.calls, 1)


if __name__ == "__main__":
    unittest.main()
