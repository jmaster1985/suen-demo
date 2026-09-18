from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import MeasurementRow
from app.schemas import Measurement, StoredMeasurement


class SqlMeasurementRepository:
    def add(self, session: Session, measurement: Measurement) -> StoredMeasurement:
        row = MeasurementRow(
            foo=measurement.foo,
            bar=measurement.bar,
            buzz=measurement.buzz,
            created_at=datetime.now(timezone.utc),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return self._to_schema(row)

    def list(
        self, session: Session, offset: int, limit: int
    ) -> tuple[list[StoredMeasurement], int]:
        rows = session.scalars(
            select(MeasurementRow).order_by(MeasurementRow.id).offset(offset).limit(limit)
        ).all()
        total = session.scalar(select(func.count()).select_from(MeasurementRow)) or 0
        return [self._to_schema(row) for row in rows], total

    @staticmethod
    def _to_schema(row: MeasurementRow) -> StoredMeasurement:
        return StoredMeasurement(
            id=row.id, foo=row.foo, bar=row.bar, buzz=row.buzz, created_at=row.created_at
        )
