from celery import Celery

from app.config import get_settings

settings = get_settings()
celery_app = Celery(
    "sensor_data_collector",
    broker=settings.rabbitmq_url,
    include=["app.tasks"],
)
celery_app.conf.update(
    accept_content=["json"],
    task_default_queue="measurements",
    task_serializer="json",
    result_serializer="json",
)
