import asyncio
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.db import get_session, initialize_database
from app.kafka import MockKafkaConsumer
from app.ports import MeasurementRepository
from app.repository import SqlMeasurementRepository
from app.schemas import MeasurementPage, SensorMessage
from app.service import MeasurementService

API_V1_PREFIX = "/api/v1"


def create_app(
    settings: Settings | None = None,
    consumer: MockKafkaConsumer | None = None,
    session_factory: sessionmaker[Session] | None = None,
    repository: MeasurementRepository | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    consumer = consumer or MockKafkaConsumer(settings.kafka_topic)
    if session_factory is None:
        from app.db import build_session_factory

        session_factory = build_session_factory(settings)
    assert session_factory is not None
    repository = repository or SqlMeasurementRepository()
    service = MeasurementService(settings, repository, session_factory)

    async def consume() -> None:
        async for payload in consumer.messages():
            consumer.record_result(service.process(payload))

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        initialize_database(session_factory)
        task = asyncio.create_task(consume())
        yield
        await consumer.close()
        await task

    app = FastAPI(title="sensor data collector", lifespan=lifespan)
    app.state.consumer = consumer
    api_v1 = APIRouter(prefix=API_V1_PREFIX, tags=["v1"])

    def session_dependency():
        yield from get_session(session_factory)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @api_v1.post("/demo/messages", status_code=202)
    async def publish_demo_message(payload: SensorMessage) -> dict[str, str]:
        await consumer.publish(payload.model_dump())
        await consumer.wait_until_idle()
        if consumer.last_result == "invalid":
            raise HTTPException(status_code=400, detail="invalid sensor payload")
        return {"status": "queued", "topic": consumer.topic}

    @api_v1.get("/measurements", response_model=MeasurementPage)
    def list_measurements(
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 20,
        session: Session = Depends(session_dependency),
    ) -> MeasurementPage:
        items, total = repository.list(session, offset=(page - 1) * page_size, limit=page_size)
        return MeasurementPage(items=items, page=page, page_size=page_size, total=total)

    app.include_router(api_v1)
    return app


app = create_app()
