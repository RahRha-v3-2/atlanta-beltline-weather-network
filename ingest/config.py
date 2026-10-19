"""Environment configuration. Secrets stay in the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://pro.weatherxm.com/api/v1"


class ConfigError(ValueError):
    """Raised when required ingest settings are missing or invalid."""


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    station_ids: tuple[str, ...]
    segment: str | None
    database_url: str | None
    qod_min_score: float

    @classmethod
    def from_env(cls) -> Settings:
        raw_ids = os.environ.get("WEATHERXM_STATION_IDS", "")
        station_ids = tuple(part.strip() for part in raw_ids.split(",") if part.strip())
        segment = os.environ.get("WEATHERXM_SEGMENT", "").strip().lower() or None
        database_url = os.environ.get("DATABASE_URL", "").strip() or None
        raw_qod = os.environ.get("QOD_MIN_SCORE", "0").strip() or "0"
        try:
            qod_min_score = float(raw_qod)
        except ValueError as exc:
            raise ConfigError("QOD_MIN_SCORE must be a number between 0 and 1") from exc
        if qod_min_score < 0 or qod_min_score > 1:
            raise ConfigError("QOD_MIN_SCORE must be a number between 0 and 1")
        base_url = os.environ.get("WEATHERXM_API_BASE_URL", DEFAULT_BASE_URL).strip()
        return cls(
            api_key=os.environ.get("WEATHERXM_API_KEY", "").strip(),
            base_url=base_url or DEFAULT_BASE_URL,
            station_ids=station_ids,
            segment=segment,
            database_url=database_url,
            qod_min_score=qod_min_score,
        )

    def require_api_key(self) -> str:
        if not self.api_key:
            raise ConfigError(
                "WEATHERXM_API_KEY is not set. Create a key in WeatherXM Pro and export it. "
                "Do not commit it."
            )
        return self.api_key
