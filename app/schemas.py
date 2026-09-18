from datetime import datetime
from typing import Annotated, Any, cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, WithJsonSchema, field_validator

SensorNumber = Annotated[Any, WithJsonSchema({"type": "number"})]


class Measurement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    foo: float
    bar: float
    buzz: float

    @field_validator("foo", "bar", "buzz", mode="before")
    @classmethod
    def finite_number(cls, value: object) -> float:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("must be a number")
        numeric_value = cast(int | float, value)
        if numeric_value != numeric_value or numeric_value in (float("inf"), float("-inf")):
            raise ValueError("must be finite")
        return float(numeric_value)

    def sanitized(self) -> "Measurement":
        return self.__class__(
            **{name: round(getattr(self, name), 4) for name in self.__class__.model_fields}
        )


class SensorMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    foo: SensorNumber
    bar: SensorNumber
    buzz: SensorNumber


class StoredMeasurement(BaseModel):
    id: UUID
    foo: float
    bar: float
    buzz: float
    created_at: datetime


class MeasurementPage(BaseModel):
    items: list[StoredMeasurement]
    page: int
    page_size: int
    total: int


def parse_payload(payload: Any) -> Measurement:
    """Parse untrusted Kafka values while preserving a useful error for logging."""
    return Measurement.model_validate(payload)
