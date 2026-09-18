import json
import logging
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.ports import MeasurementRepository
from app.schemas import parse_payload

logger = logging.getLogger("uvicorn.error")


class MeasurementService:
    def __init__(
        self,
        settings: Settings,
        repository: MeasurementRepository,
        sessions: sessionmaker[Session],
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.sessions = sessions

    def process(self, payload: Any) -> str:
        try:
            measurement = parse_payload(payload)
        except Exception:
            self._log_event(payload, logging.ERROR, "invalid sensor data")
            return "invalid"

        outlier_fields = [
            name
            for name, (minimum, maximum) in self.settings.thresholds.items()
            if not minimum <= getattr(measurement, name) <= maximum
        ]
        if outlier_fields:
            self._log_event(payload, logging.WARNING, "outlier detected")
            return "outlier"

        with self.sessions() as session:
            self.repository.add(session, measurement.sanitized())
        return "stored"

    def _log_event(self, value: Any, level: int, message: str) -> None:
        body = json.dumps(value, default=str, separators=(",", ":"))
        logger.log(level, "%s: %s", message, body)
