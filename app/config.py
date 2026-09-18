from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _yaml_thresholds() -> dict[str, dict[str, float]]:
    path = Path(__file__).parents[1] / "config" / "settings.yaml"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as settings_file:
        return yaml.safe_load(settings_file) or {}


_THRESHOLDS = _yaml_thresholds()


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://app:app@localhost:5432/app"
    kafka_topic: str = "measurements"
    foo_min: float = _THRESHOLDS.get("foo", {}).get("min", -100)
    foo_max: float = _THRESHOLDS.get("foo", {}).get("max", 100)
    bar_min: float = _THRESHOLDS.get("bar", {}).get("min", -100)
    bar_max: float = _THRESHOLDS.get("bar", {}).get("max", 100)
    buzz_min: float = _THRESHOLDS.get("buzz", {}).get("min", -100)
    buzz_max: float = _THRESHOLDS.get("buzz", {}).get("max", 100)
    consumer_poll_seconds: float = Field(default=0.1, gt=0)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def thresholds(self) -> dict[str, tuple[float, float]]:
        return {
            "foo": (self.foo_min, self.foo_max),
            "bar": (self.bar_min, self.bar_max),
            "buzz": (self.buzz_min, self.buzz_max),
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
