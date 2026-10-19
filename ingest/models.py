"""Types aligned with the WeatherXM Pro API observation schema.

Field names on the wire use WeatherXM's JSON. Stored and public records use
explicit units so a reading is not ambiguous.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

SEGMENTS = frozenset({"eastside", "westside"})


def _num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


@dataclass(frozen=True)
class Location:
    lat: float | None = None
    lon: float | None = None
    elevation: float | None = None


@dataclass(frozen=True)
class Health:
    timestamp: str | None = None
    data_quality_score: float | None = None
    location_quality_score: float | None = None
    location_quality_reason: str | None = None


@dataclass(frozen=True)
class Observation:
    timestamp: str
    temperature: float | None = None
    feels_like: float | None = None
    dew_point: float | None = None
    humidity: float | None = None
    precipitation_rate: float | None = None
    precipitation_accumulated: float | None = None
    wind_speed: float | None = None
    wind_gust: float | None = None
    wind_direction: int | None = None
    uv_index: float | None = None
    pressure: float | None = None
    solar_irradiance: float | None = None
    icon: str | None = None


@dataclass(frozen=True)
class Station:
    id: str
    name: str | None = None
    cell_index: str | None = None
    location: Location | None = None
    created_at: str | None = None


@dataclass(frozen=True)
class LatestReading:
    station_id: str
    observation: Observation
    health: Health | None = None
    location: Location | None = None
    station_name: str | None = None
    cell_index: str | None = None


@dataclass(frozen=True)
class TrailObservation:
    """One stored reading. `segment` is our label, not a WeatherXM field."""

    station_id: str
    observed_at: str
    station_name: str | None = None
    segment: str | None = None
    cell_index: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    elevation_m: float | None = None
    temperature_c: float | None = None
    feels_like_c: float | None = None
    dew_point_c: float | None = None
    humidity_pct: float | None = None
    precipitation_rate_mm_h: float | None = None
    precipitation_accumulated_mm: float | None = None
    wind_speed_m_s: float | None = None
    wind_gust_m_s: float | None = None
    wind_direction_deg: int | None = None
    uv_index: float | None = None
    pressure_hpa: float | None = None
    solar_irradiance_w_m2: float | None = None
    icon: str | None = None
    qod_score: float | None = None
    source: str = "weatherxm"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_location(payload: Any) -> Location | None:
    if not isinstance(payload, dict):
        return None
    return Location(
        lat=_num(payload.get("lat")),
        lon=_num(payload.get("lon")),
        elevation=_num(payload.get("elevation")),
    )


def parse_health(payload: Any) -> Health | None:
    if not isinstance(payload, dict):
        return None
    data_quality = payload.get("data_quality") or {}
    location_quality = payload.get("location_quality") or {}
    if not isinstance(data_quality, dict):
        data_quality = {}
    if not isinstance(location_quality, dict):
        location_quality = {}
    return Health(
        timestamp=payload.get("timestamp") if isinstance(payload.get("timestamp"), str) else None,
        data_quality_score=_num(data_quality.get("score")),
        location_quality_score=_num(location_quality.get("score")),
        location_quality_reason=(
            location_quality.get("reason")
            if isinstance(location_quality.get("reason"), str)
            else None
        ),
    )


def parse_observation(payload: Any) -> Observation:
    if not isinstance(payload, dict):
        raise ValueError("Observation payload must be an object")
    timestamp = payload.get("timestamp")
    if not isinstance(timestamp, str) or not timestamp:
        raise ValueError("Observation is missing a timestamp")
    return Observation(
        timestamp=timestamp,
        temperature=_num(payload.get("temperature")),
        feels_like=_num(payload.get("feels_like")),
        dew_point=_num(payload.get("dew_point")),
        humidity=_num(payload.get("humidity")),
        precipitation_rate=_num(payload.get("precipitation_rate")),
        precipitation_accumulated=_num(payload.get("precipitation_accumulated")),
        wind_speed=_num(payload.get("wind_speed")),
        wind_gust=_num(payload.get("wind_gust")),
        wind_direction=_int(payload.get("wind_direction")),
        uv_index=_num(payload.get("uv_index")),
        pressure=_num(payload.get("pressure")),
        solar_irradiance=_num(payload.get("solar_irradiance")),
        icon=payload.get("icon") if isinstance(payload.get("icon"), str) else None,
    )


def parse_latest(station_id: str, payload: Any) -> LatestReading:
    if not isinstance(payload, dict):
        raise ValueError("Latest payload must be an object")
    return LatestReading(
        station_id=station_id,
        observation=parse_observation(payload.get("observation")),
        health=parse_health(payload.get("health")),
        location=parse_location(payload.get("location")),
    )


def parse_history_observations(payload: Any) -> list[Observation]:
    """Accept a single history object or a list of them.

    The published schema describes one day object with an `observations` array.
    A multi-day range is handled if the service returns a list of those objects.
    """

    blocks = payload if isinstance(payload, list) else [payload]
    observations: list[Observation] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        raw_items = block.get("observations") or []
        if not isinstance(raw_items, list):
            continue
        observations.extend(parse_observation(item) for item in raw_items)
    return observations


def to_trail_observation(
    reading: LatestReading,
    *,
    segment: str | None = None,
    station_name: str | None = None,
    cell_index: str | None = None,
) -> TrailObservation:
    if segment is not None and segment not in SEGMENTS:
        raise ValueError(f"segment must be one of {sorted(SEGMENTS)}")
    location = reading.location
    health = reading.health
    obs = reading.observation
    return TrailObservation(
        station_id=reading.station_id,
        observed_at=obs.timestamp,
        station_name=station_name or reading.station_name,
        segment=segment,
        cell_index=cell_index or reading.cell_index,
        latitude=location.lat if location else None,
        longitude=location.lon if location else None,
        elevation_m=location.elevation if location else None,
        temperature_c=obs.temperature,
        feels_like_c=obs.feels_like,
        dew_point_c=obs.dew_point,
        humidity_pct=obs.humidity,
        precipitation_rate_mm_h=obs.precipitation_rate,
        precipitation_accumulated_mm=obs.precipitation_accumulated,
        wind_speed_m_s=obs.wind_speed,
        wind_gust_m_s=obs.wind_gust,
        wind_direction_deg=obs.wind_direction,
        uv_index=obs.uv_index,
        pressure_hpa=obs.pressure,
        solar_irradiance_w_m2=obs.solar_irradiance,
        icon=obs.icon,
        qod_score=health.data_quality_score if health else None,
    )
