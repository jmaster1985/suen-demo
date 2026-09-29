import httpx
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.main import create_app
from app.schemas import Measurement
from tests.fakes import InMemoryMeasurementRepository


class RecordingTask:
    def __init__(self, repository):
        self.repository = repository
        self.payloads = []

    def delay(self, payload):
        self.payloads.append(payload)


async def test_measurements_endpoint_supports_pagination(tmp_path):
    settings = Settings(
        database_url="postgresql+psycopg://unused",
    )
    repository = InMemoryMeasurementRepository()
    repository.add(None, Measurement(foo=1, bar=2, buzz=3))
    repository.add(None, Measurement(foo=4, bar=5, buzz=6))
    app = create_app(settings, sessionmaker(), repository, RecordingTask(repository))

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/measurements?page=2&page_size=1")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 1
    assert body["items"][0]["foo"] == 4


async def test_invalid_message_returns_bad_request(tmp_path):
    settings = Settings(database_url="postgresql+psycopg://unused")
    task = RecordingTask(InMemoryMeasurementRepository())
    app = create_app(settings, sessionmaker(), task.repository, task)

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/demo/messages",
                json={"foo": 10, "bar": 20, "buzz": "invalid-number"},
            )

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid sensor payload"
    assert task.payloads == []


async def test_valid_message_is_sanitized_before_being_queued():
    settings = Settings(database_url="postgresql+psycopg://unused")
    task = RecordingTask(InMemoryMeasurementRepository())
    app = create_app(settings, sessionmaker(), task.repository, task)

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/demo/messages",
                json={"foo": 1.234567, "bar": 2, "buzz": 3},
            )

    assert response.status_code == 202
    assert response.json() == {"status": "queued"}
    assert task.payloads == [{"foo": 1.2346, "bar": 2.0, "buzz": 3.0}]
