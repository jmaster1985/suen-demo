from app.celery_app import celery_app
from app.config import get_settings
from app.db import build_session_factory
from app.repository import SqlMeasurementRepository
from app.service import MeasurementService


@celery_app.task(name="process_measurement")
def process_measurement(payload: dict[str, float]) -> str:
    settings = get_settings()
    sessions = build_session_factory(settings)
    service = MeasurementService(settings, SqlMeasurementRepository(), sessions)
    return service.process(payload)
