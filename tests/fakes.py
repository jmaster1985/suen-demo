from datetime import datetime, timezone
from uuid import uuid4

from app.schemas import Measurement, StoredMeasurement


class InMemoryMeasurementRepository:
    def __init__(self) -> None:
        self.items: list[StoredMeasurement] = []

    def add(self, session: object, measurement: Measurement) -> StoredMeasurement:
        item = StoredMeasurement(
            id=uuid4(),
            foo=measurement.foo,
            bar=measurement.bar,
            buzz=measurement.buzz,
            created_at=datetime.now(timezone.utc),
        )
        self.items.append(item)
        return item

    def list(self, session: object, offset: int, limit: int) -> tuple[list[StoredMeasurement], int]:
        return self.items[offset : offset + limit], len(self.items)
