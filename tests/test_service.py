import json
import logging

from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.service import MeasurementService
from tests.fakes import InMemoryMeasurementRepository


def make_service(tmp_path):
    settings = Settings(
        database_url="postgresql+psycopg://unused",
        foo_min=0,
        foo_max=10,
        bar_min=0,
        bar_max=10,
        buzz_min=0,
        buzz_max=10,
    )
    return MeasurementService(settings, InMemoryMeasurementRepository(), sessionmaker())


def test_in_range_values_are_sanitized_and_stored(tmp_path):
    service = make_service(tmp_path)

    assert service.process({"foo": 1.234567, "bar": 2, "buzz": 3}) == "stored"

    with service.sessions() as session:
        rows, total = service.repository.list(session, 0, 10)
    assert total == 1
    assert rows[0].foo == 1.2346


def test_outlier_is_logged_and_not_stored(tmp_path, caplog):
    service = make_service(tmp_path)

    with caplog.at_level(logging.WARNING, logger="uvicorn.error"):
        assert service.process({"foo": 11, "bar": 2, "buzz": 3}) == "outlier"

    with service.sessions() as session:
        _, total = service.repository.list(session, 0, 10)
    assert total == 0
    assert caplog.records[0].message.startswith("outlier detected: ")
    assert json.loads(caplog.records[0].message.removeprefix("outlier detected: "))["foo"] == 11


def test_corrupt_payload_is_logged_as_error(tmp_path, caplog):
    service = make_service(tmp_path)

    with caplog.at_level(logging.ERROR, logger="uvicorn.error"):
        assert service.process({"foo": "not-a-number", "bar": 2, "buzz": 3}) == "invalid"
    assert caplog.records[0].levelno == logging.ERROR
    assert caplog.records[0].message.startswith("invalid sensor data: ")
    assert (
        json.loads(caplog.records[0].message.removeprefix("invalid sensor data: "))["foo"]
        == "not-a-number"
    )
