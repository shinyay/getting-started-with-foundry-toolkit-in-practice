import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from azure.core.exceptions import HttpResponseError, ServiceRequestError

from gateway.settings import GatewaySettings
from scripts.memory_polling import (
    _run_with_retry,
    is_retryable_memory_error,
    wait_for_memory_proof,
)
from gateway.memory_proof import MemoryProof

PROOF = MemoryProof(
    "akg0123456789abcdef",
    "akvfedcba9876543210",
)
SETTINGS = GatewaySettings(
    project_endpoint="https://example.test/api/projects/demo",
    model_deployment="chat",
    memory_store_name="memory",
    memory_scope="scope",
)


def memory_items(*contents: str) -> list[SimpleNamespace]:
    return [SimpleNamespace(content=content) for content in contents]


class FakeAsyncItems:
    def __init__(self, outcome: object) -> None:
        self.error = outcome if isinstance(outcome, BaseException) else None
        self.items = iter([] if self.error else outcome)

    def __aiter__(self) -> "FakeAsyncItems":
        return self

    async def __anext__(self) -> object:
        if self.error:
            error = self.error
            self.error = None
            raise error
        try:
            return next(self.items)
        except StopIteration as error:
            raise StopAsyncIteration from error


class FakeMemoryStores:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = outcomes
        self.index = 0

    def list_memories(self, **_: object) -> FakeAsyncItems:
        outcome = self.outcomes[min(self.index, len(self.outcomes) - 1)]
        self.index += 1
        return FakeAsyncItems(outcome)


def fake_project(*outcomes: object) -> SimpleNamespace:
    stores = FakeMemoryStores(list(outcomes))
    return SimpleNamespace(
        beta=SimpleNamespace(memory_stores=stores),
        stores=stores,
    )


def http_error(status_code: int) -> HttpResponseError:
    response = SimpleNamespace(
        status_code=status_code,
        reason="test",
        headers={},
    )
    return HttpResponseError(message="test", response=response)


class RetryClassificationTests(unittest.TestCase):
    def test_transient_status_and_transport_errors_retry(self) -> None:
        self.assertTrue(is_retryable_memory_error(http_error(429)))
        self.assertTrue(
            is_retryable_memory_error(ServiceRequestError("temporary"))
        )

    def test_non_retryable_client_error_fails_fast(self) -> None:
        self.assertFalse(is_retryable_memory_error(http_error(400)))


class MemoryPollingTests(unittest.IsolatedAsyncioTestCase):
    async def test_transient_error_then_exact_pair_succeeds(self) -> None:
        project = fake_project(
            ServiceRequestError("temporary"),
            memory_items(f"Stored pair: {PROOF.pair}"),
        )
        with patch(
            "scripts.memory_polling.asyncio.sleep",
            new=AsyncMock(),
        ):
            contents = await wait_for_memory_proof(
                project,
                SETTINGS,
                PROOF,
                timeout=1,
                poll_interval=0,
            )
        self.assertIn(PROOF.pair, contents[0])
        self.assertEqual(project.stores.index, 2)

    async def test_non_retryable_error_is_raised_immediately(self) -> None:
        project = fake_project(http_error(400))
        with self.assertRaises(HttpResponseError):
            await wait_for_memory_proof(
                project,
                SETTINGS,
                PROOF,
                timeout=1,
                poll_interval=0,
            )
        self.assertEqual(project.stores.index, 1)

    async def test_timeout_preserves_last_transient_error(self) -> None:
        project = fake_project(ServiceRequestError("temporary"))
        with self.assertRaises(TimeoutError) as raised:
            await wait_for_memory_proof(
                project,
                SETTINGS,
                PROOF,
                timeout=0.01,
                poll_interval=0.02,
            )
        self.assertIsInstance(raised.exception.__cause__, ServiceRequestError)

    async def test_missing_pair_reports_proof_timeout(self) -> None:
        project = fake_project(memory_items("unrelated memory"))
        with self.assertRaisesRegex(
            TimeoutError,
            "Foundry Memory did not return this run's exact key/value pair",
        ):
            await wait_for_memory_proof(
                project,
                SETTINGS,
                PROOF,
                timeout=0.01,
                poll_interval=0.02,
            )

    async def test_timeout_cancels_in_flight_operation(self) -> None:
        cancelled = asyncio.Event()

        async def stalled_operation() -> None:
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        with self.assertRaisesRegex(
            TimeoutError,
            "within 0.01 seconds",
        ):
            await _run_with_retry(stalled_operation, timeout=0.01)

        self.assertTrue(cancelled.is_set())


if __name__ == "__main__":
    unittest.main()
