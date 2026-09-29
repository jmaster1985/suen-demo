import json
import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.db import get_session, initialize_database
from app.ports import MeasurementRepository, MeasurementTask
from app.repository import SqlMeasurementRepository
from app.schemas import MeasurementPage, SensorMessage, parse_payload

API_V1_PREFIX = "/api/v1"
logger = logging.getLogger("uvicorn.error")


def create_app(
    settings: Settings | None = None,
    session_factory: sessionmaker[Session] | None = None,
    repository: MeasurementRepository | None = None,
    task: MeasurementTask | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    if session_factory is None:
        from app.db import build_session_factory

        session_factory = build_session_factory(settings)
    assert session_factory is not None
    repository = repository or SqlMeasurementRepository()
    if task is None:
        from app.tasks import process_measurement

        task = process_measurement

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        initialize_database(session_factory)
        yield

    app = FastAPI(title="sensor data collector", lifespan=lifespan)
    api_v1 = APIRouter(prefix=API_V1_PREFIX, tags=["v1"])

    def session_dependency():
        yield from get_session(session_factory)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @api_v1.post("/demo/messages", status_code=202)
    async def publish_demo_message(payload: SensorMessage) -> dict[str, str]:
        try:
            sanitized = parse_payload(payload.model_dump()).sanitized()
        except ValidationError:
            body = json.dumps(payload.model_dump(), separators=(",", ":"))
            logger.error("invalid sensor data: %s", body)
            raise HTTPException(status_code=400, detail="invalid sensor payload")
        task.delay(sanitized.model_dump())
        return {"status": "queued"}

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
