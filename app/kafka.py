import asyncio
from collections.abc import AsyncIterator
from typing import Any


class MockKafkaConsumer:
    """A deterministic Kafka stand-in; replace this adapter without changing business code."""

    def __init__(self, topic: str = "measurements") -> None:
        self.topic = topic
        self._queue: asyncio.Queue[Any] = asyncio.Queue()
        self._closed = False
        self._last_result: str | None = None

    async def publish(self, payload: Any) -> None:
        await self._queue.put(payload)

    async def wait_until_idle(self) -> None:
        await self._queue.join()

    @property
    def last_result(self) -> str | None:
        return self._last_result

    def record_result(self, result: str) -> None:
        self._last_result = result

    async def messages(self) -> AsyncIterator[Any]:
        while not self._closed:
            payload = await self._queue.get()
            try:
                yield payload
            finally:
                self._queue.task_done()

    async def close(self) -> None:
        self._closed = True
        await self._queue.put(None)
