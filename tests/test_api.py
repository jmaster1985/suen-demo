import httpx
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.kafka import MockKafkaConsumer
from app.main import create_app
from tests.fakes import InMemoryMeasurementRepository


async def test_measurements_endpoint_supports_pagination(tmp_path):
    settings = Settings(
        database_url="postgresql+psycopg://unused",
    )
    consumer = MockKafkaConsumer()
    app = create_app(settings, consumer, sessionmaker(), InMemoryMeasurementRepository())

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await consumer.publish({"foo": 1, "bar": 2, "buzz": 3})
            await consumer.publish({"foo": 4, "bar": 5, "buzz": 6})
            response = await client.get("/api/v1/measurements?page=2&page_size=1")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 1
    assert body["items"][0]["foo"] == 4


async def test_invalid_message_returns_bad_request(tmp_path):
    settings = Settings(database_url="postgresql+psycopg://unused")
    consumer = MockKafkaConsumer()
    app = create_app(settings, consumer, sessionmaker(), InMemoryMeasurementRepository())

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/demo/messages",
                json={"foo": 10, "bar": 20, "buzz": "invalid-number"},
            )

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid sensor payload"
