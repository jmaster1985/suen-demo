from collections.abc import AsyncIterator
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.schemas import Measurement, StoredMeasurement


class MessageConsumer(Protocol):
    async def messages(self) -> AsyncIterator[Any]: ...


class MeasurementRepository(Protocol):
    def add(self, session: Session, measurement: Measurement) -> StoredMeasurement: ...
    def list(
        self, session: Session, offset: int, limit: int
    ) -> tuple[list[StoredMeasurement], int]: ...
