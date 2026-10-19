"""Observation storage.

`MemoryStore` is the default when DATABASE_URL is unset, so the API and tests
run with no database. `PostgresStore` writes the Timescale schema in db/schema.sql.
Neither store ships with stations.
"""

from __future__ import annotations

import os
from dataclasses import replace
from datetime import UTC, datetime
from typing import Protocol

from ingest.models import SEGMENTS, TrailObservation


class Store(Protocol):
    def ping(self) -> bool: ...

    def save(self, row: TrailObservation) -> None: ...

    def list_stations(self, segment: str | None = None) -> list[dict[str, object]]: ...

    def latest_observations(self, segment: str | None = None) -> list[TrailObservation]: ...

    def kind(self) -> str: ...


def store_from_env() -> Store:
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return PostgresStore(url)
    return MemoryStore()


def _validate(row: TrailObservation) -> None:
    if not row.station_id:
        raise ValueError("station_id is required")
    if not row.observed_at:
        raise ValueError("observed_at is required")
    if row.segment is not None and row.segment not in SEGMENTS:
        raise ValueError(f"segment must be one of {sorted(SEGMENTS)} or null")
    if row.source != "weatherxm":
        raise ValueError("observations from this ingest path must use source 'weatherxm'")


def _parse_ts(value: str) -> datetime:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


class MemoryStore:
    def __init__(self) -> None:
        self._stations: dict[str, dict[str, object]] = {}
        self._rows: dict[tuple[str, str], TrailObservation] = {}

    def ping(self) -> bool:
        return True

    def kind(self) -> str:
        return "memory"

    def save(self, row: TrailObservation) -> None:
        _validate(row)
        # Match the Postgres COALESCE upsert: a later reading does not clear a label
        # just because this call omitted it.
        previous = self._stations.get(row.station_id, {})
        merged = {
            "station_name": _coalesce(row.station_name, previous.get("station_name")),
            "segment": _coalesce(row.segment, previous.get("segment")),
            "cell_index": _coalesce(row.cell_index, previous.get("cell_index")),
            "latitude": _coalesce(row.latitude, previous.get("latitude")),
            "longitude": _coalesce(row.longitude, previous.get("longitude")),
            "elevation_m": _coalesce(row.elevation_m, previous.get("elevation_m")),
        }
        self._stations[row.station_id] = merged
        stored = replace(row, **merged)
        self._rows[(row.station_id, row.observed_at)] = stored

    def list_stations(self, segment: str | None = None) -> list[dict[str, object]]:
        by_station: dict[str, TrailObservation] = {}
        for row in self._rows.values():
            if segment is not None and row.segment != segment:
                continue
            current = by_station.get(row.station_id)
            if current is None or _parse_ts(row.observed_at) >= _parse_ts(current.observed_at):
                by_station[row.station_id] = row
        stations = [
            {
                "id": row.station_id,
                "name": row.station_name,
                "segment": row.segment,
                "cell_index": row.cell_index,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "elevation_m": row.elevation_m,
            }
            for row in by_station.values()
        ]
        return sorted(stations, key=lambda item: str(item["id"]))

    def latest_observations(self, segment: str | None = None) -> list[TrailObservation]:
        by_station: dict[str, TrailObservation] = {}
        for row in self._rows.values():
            if segment is not None and row.segment != segment:
                continue
            current = by_station.get(row.station_id)
            if current is None or _parse_ts(row.observed_at) >= _parse_ts(current.observed_at):
                by_station[row.station_id] = row
        return sorted(by_station.values(), key=lambda row: row.station_id)


class PostgresStore:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def kind(self) -> str:
        return "postgres"

    def ping(self) -> bool:
        try:
            with self._connect() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    def save(self, row: TrailObservation) -> None:
        _validate(row)
        observed_at = _parse_ts(row.observed_at)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO stations (
                    id, name, cell_index, segment, latitude, longitude, elevation_m, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                    name = COALESCE(EXCLUDED.name, stations.name),
                    cell_index = COALESCE(EXCLUDED.cell_index, stations.cell_index),
                    segment = COALESCE(EXCLUDED.segment, stations.segment),
                    latitude = COALESCE(EXCLUDED.latitude, stations.latitude),
                    longitude = COALESCE(EXCLUDED.longitude, stations.longitude),
                    elevation_m = COALESCE(EXCLUDED.elevation_m, stations.elevation_m),
                    updated_at = now()
                """,
                (
                    row.station_id,
                    row.station_name,
                    row.cell_index,
                    row.segment,
                    row.latitude,
                    row.longitude,
                    row.elevation_m,
                ),
            )
            conn.execute(
                """
                INSERT INTO observations (
                    station_id, observed_at, temperature_c, feels_like_c, dew_point_c,
                    humidity_pct, precipitation_rate_mm_h, precipitation_accumulated_mm,
                    wind_speed_m_s, wind_gust_m_s, wind_direction_deg, uv_index,
                    pressure_hpa, solar_irradiance_w_m2, icon, qod_score, source, license
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    'weatherxm', 'WeatherXM terms'
                )
                ON CONFLICT (station_id, observed_at) DO UPDATE SET
                    temperature_c = EXCLUDED.temperature_c,
                    feels_like_c = EXCLUDED.feels_like_c,
                    dew_point_c = EXCLUDED.dew_point_c,
                    humidity_pct = EXCLUDED.humidity_pct,
                    precipitation_rate_mm_h = EXCLUDED.precipitation_rate_mm_h,
                    precipitation_accumulated_mm = EXCLUDED.precipitation_accumulated_mm,
                    wind_speed_m_s = EXCLUDED.wind_speed_m_s,
                    wind_gust_m_s = EXCLUDED.wind_gust_m_s,
                    wind_direction_deg = EXCLUDED.wind_direction_deg,
                    uv_index = EXCLUDED.uv_index,
                    pressure_hpa = EXCLUDED.pressure_hpa,
                    solar_irradiance_w_m2 = EXCLUDED.solar_irradiance_w_m2,
                    icon = EXCLUDED.icon,
                    qod_score = EXCLUDED.qod_score
                """,
                (
                    row.station_id,
                    observed_at,
                    row.temperature_c,
                    row.feels_like_c,
                    row.dew_point_c,
                    row.humidity_pct,
                    row.precipitation_rate_mm_h,
                    row.precipitation_accumulated_mm,
                    row.wind_speed_m_s,
                    row.wind_gust_m_s,
                    row.wind_direction_deg,
                    row.uv_index,
                    row.pressure_hpa,
                    row.solar_irradiance_w_m2,
                    row.icon,
                    row.qod_score,
                ),
            )

    def list_stations(self, segment: str | None = None) -> list[dict[str, object]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, name, segment, cell_index, latitude, longitude, elevation_m
                FROM stations
                WHERE (%s::text IS NULL OR segment = %s)
                ORDER BY id
                """,
                (segment, segment),
            ).fetchall()
        return [dict(row) for row in rows]

    def latest_observations(self, segment: str | None = None) -> list[TrailObservation]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT ON (o.station_id)
                    o.station_id,
                    s.name AS station_name,
                    s.segment,
                    s.cell_index,
                    s.latitude,
                    s.longitude,
                    s.elevation_m,
                    o.observed_at,
                    o.temperature_c,
                    o.feels_like_c,
                    o.dew_point_c,
                    o.humidity_pct,
                    o.precipitation_rate_mm_h,
                    o.precipitation_accumulated_mm,
                    o.wind_speed_m_s,
                    o.wind_gust_m_s,
                    o.wind_direction_deg,
                    o.uv_index,
                    o.pressure_hpa,
                    o.solar_irradiance_w_m2,
                    o.icon,
                    o.qod_score,
                    o.source
                FROM observations o
                JOIN stations s ON s.id = o.station_id
                WHERE (%s::text IS NULL OR s.segment = %s)
                ORDER BY o.station_id, o.observed_at DESC
                """,
                (segment, segment),
            ).fetchall()
        return [_row_to_observation(row) for row in rows]

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(self.database_url, row_factory=dict_row)


def _row_to_observation(row: dict[str, object]) -> TrailObservation:
    observed_at = row["observed_at"]
    if isinstance(observed_at, datetime):
        stamp = observed_at.isoformat()
    else:
        stamp = str(observed_at)
    return TrailObservation(
        station_id=str(row["station_id"]),
        observed_at=stamp,
        station_name=_optional_str(row.get("station_name")),
        segment=_optional_str(row.get("segment")),
        cell_index=_optional_str(row.get("cell_index")),
        latitude=_optional_float(row.get("latitude")),
        longitude=_optional_float(row.get("longitude")),
        elevation_m=_optional_float(row.get("elevation_m")),
        temperature_c=_optional_float(row.get("temperature_c")),
        feels_like_c=_optional_float(row.get("feels_like_c")),
        dew_point_c=_optional_float(row.get("dew_point_c")),
        humidity_pct=_optional_float(row.get("humidity_pct")),
        precipitation_rate_mm_h=_optional_float(row.get("precipitation_rate_mm_h")),
        precipitation_accumulated_mm=_optional_float(row.get("precipitation_accumulated_mm")),
        wind_speed_m_s=_optional_float(row.get("wind_speed_m_s")),
        wind_gust_m_s=_optional_float(row.get("wind_gust_m_s")),
        wind_direction_deg=_optional_int(row.get("wind_direction_deg")),
        uv_index=_optional_float(row.get("uv_index")),
        pressure_hpa=_optional_float(row.get("pressure_hpa")),
        solar_irradiance_w_m2=_optional_float(row.get("solar_irradiance_w_m2")),
        icon=_optional_str(row.get("icon")),
        qod_score=_optional_float(row.get("qod_score")),
        source=str(row.get("source") or "weatherxm"),
    )


def _coalesce(new: object, old: object) -> object:
    return old if new is None else new


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _optional_float(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    return None
