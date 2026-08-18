"""Bounded retry and polling helpers for authoritative Memory proof."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from azure.core.exceptions import (
    HttpResponseError,
    ServiceRequestError,
    ServiceResponseError,
)

from gateway.memory_proof import MemoryProof, has_memory_proof
from gateway.settings import GatewaySettings

T = TypeVar("T")

RETRYABLE_STATUS_CODES = frozenset(
    {401, 403, 408, 409, 429, 500, 502, 503, 504}
)


class _MemoryOperationDeadlineExceeded(Exception):
    pass


async def _await_before_deadline(
    awaitable: Awaitable[T],
    timeout: float,
) -> T:
    """Cancel an in-flight operation when its remaining budget expires."""
    task = asyncio.ensure_future(awaitable)
    done, _ = await asyncio.wait({task}, timeout=timeout)
    if task not in done:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        raise _MemoryOperationDeadlineExceeded
    return task.result()


def response_status_code(error: HttpResponseError) -> int | None:
    """Read an HTTP status from either supported Azure error shape."""
    status = getattr(error, "status_code", None)
    if status is not None:
        return int(status)
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    return int(status) if status is not None else None


def is_retryable_memory_error(error: BaseException) -> bool:
    """Return whether an explicit proof operation may retry this error."""
    if isinstance(error, (ServiceRequestError, ServiceResponseError)):
        return True
    if isinstance(error, HttpResponseError):
        return response_status_code(error) in RETRYABLE_STATUS_CODES
    return False


async def list_memory_contents(
    project: Any,
    settings: GatewaySettings,
) -> list[str]:
    """List authoritative Memory items once and return their content."""
    items = project.beta.memory_stores.list_memories(
        name=settings.memory_store_name,
        scope=settings.memory_scope,
    )
    return [item.content async for item in items]


async def _run_with_retry(
    operation: Callable[[], Awaitable[T]],
    timeout: float,
    poll_interval: float = 5.0,
) -> T:
    """Retry one Memory operation only for known transient failures."""
    if timeout < 0:
        raise ValueError("timeout must be zero or greater")
    deadline = time.monotonic() + timeout
    last_error: BaseException | None = None

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            message = (
                "Memory operation did not complete within "
                f"{timeout:g} seconds."
            )
            raise TimeoutError(message) from last_error
        try:
            return await _await_before_deadline(operation(), remaining)
        except _MemoryOperationDeadlineExceeded as error:
            message = (
                "Memory operation did not complete within "
                f"{timeout:g} seconds."
            )
            raise TimeoutError(message) from (last_error or error)
        except (
            HttpResponseError,
            ServiceRequestError,
            ServiceResponseError,
        ) as error:
            if not is_retryable_memory_error(error):
                raise
            last_error = error

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            message = (
                "Memory operation did not complete within "
                f"{timeout:g} seconds."
            )
            raise TimeoutError(message) from last_error
        await asyncio.sleep(min(poll_interval, remaining))


async def list_memory_contents_with_retry(
    project: Any,
    settings: GatewaySettings,
    timeout: float,
    poll_interval: float = 5.0,
) -> list[str]:
    """List Memory items with bounded retry for transient failures."""
    return await _run_with_retry(
        lambda: list_memory_contents(project, settings),
        timeout,
        poll_interval,
    )


async def wait_for_memory_proof(
    project: Any,
    settings: GatewaySettings,
    proof: MemoryProof,
    timeout: float,
    poll_interval: float = 5.0,
) -> list[str]:
    """Poll until one Memory item contains the exact current proof pair."""
    if timeout < 0:
        raise ValueError("timeout must be zero or greater")
    deadline = time.monotonic() + timeout

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(
                "The memory store did not return this run's exact key/value "
                f"pair within {timeout:g} seconds: {proof.pair}"
            )
        contents = await list_memory_contents_with_retry(
            project,
            settings,
            timeout=remaining,
            poll_interval=poll_interval,
        )
        if has_memory_proof(contents, proof):
            return contents

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(
                "The memory store did not return this run's exact key/value "
                f"pair within {timeout:g} seconds: {proof.pair}"
            )
        await asyncio.sleep(min(poll_interval, remaining))
