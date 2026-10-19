"""Client for the public WeatherXM Pro API.

Verified against the live OpenAPI document on 2026-10-19:

- Spec: https://pro.weatherxm.com/api/v1/spec (OpenAPI 3.1.0, version 1.13.4)
- Docs: https://pro.weatherxm.com/docs
- Server: https://pro.weatherxm.com/api/v1
- Auth: header `X-API-KEY` (security scheme ApiKeyAuth)

An unauthenticated GET of `/api/v1/stations/{id}/latest` returns HTTP 401
with `{"message":"API key is missing"}`.

Observations for a station:

- GET /stations/{station_id}/latest
- GET /stations/{station_id}/history?date=YYYY-MM-DD
- GET /stations/{station_id}/history?start=YYYY-MM-DD&end=YYYY-MM-DD
  (range cannot exceed 7 days)
- GET /stations/{station_id}/health

The station-owner network API at https://api.weatherxm.com/api/v1 uses a
bearer token and is a different surface. This client does not call it.
"""

from __future__ import annotations

from typing import Any

import httpx

from ingest.config import DEFAULT_BASE_URL
from ingest.models import (
    Health,
    LatestReading,
    Observation,
    parse_health,
    parse_history_observations,
    parse_latest,
)

USER_AGENT = "beltline-telemetry/0.1"


class WeatherXMError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class WeatherXMClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        *,
        http: httpx.Client | None = None,
        timeout: float = 30.0,
    ) -> None:
        if not api_key or not api_key.strip():
            raise WeatherXMError(
                "WEATHERXM_API_KEY is not set. The WeatherXM Pro API requires the X-API-KEY header."
            )
        self.base_url = base_url.rstrip("/")
        self._owns_http = http is None
        self._http = http or httpx.Client(
            base_url=self.base_url,
            headers={
                "X-API-KEY": api_key.strip(),
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
            timeout=timeout,
        )

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> WeatherXMClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def latest(self, station_id: str) -> LatestReading:
        payload = self._get(f"stations/{station_id}/latest")
        reading = parse_latest(station_id, payload)
        if reading.health is None or reading.health.data_quality_score is None:
            health = self._health_or_none(station_id)
            if health is not None:
                reading = LatestReading(
                    station_id=reading.station_id,
                    observation=reading.observation,
                    health=health,
                    location=reading.location,
                    station_name=reading.station_name,
                    cell_index=reading.cell_index,
                )
        return reading

    def history(
        self,
        station_id: str,
        *,
        on_date: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> list[Observation]:
        params: dict[str, str] = {}
        if on_date:
            params["date"] = on_date
        elif start and end:
            params["start"] = start
            params["end"] = end
        else:
            raise WeatherXMError("history requires date, or both start and end (YYYY-MM-DD, UTC)")
        payload = self._get(f"stations/{station_id}/history", params=params)
        return parse_history_observations(payload)

    def health(self, station_id: str) -> Health | None:
        payload = self._get(f"stations/{station_id}/health")
        if not isinstance(payload, dict):
            return None
        return parse_health(payload.get("health"))

    def _health_or_none(self, station_id: str) -> Health | None:
        try:
            return self.health(station_id)
        except WeatherXMError:
            return None

    def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        try:
            response = self._http.get(path, params=params)
        except httpx.HTTPError as exc:
            raise WeatherXMError(f"WeatherXM request failed: {exc}") from exc
        if response.status_code >= 400:
            detail = _error_detail(response)
            raise WeatherXMError(
                f"WeatherXM API returned HTTP {response.status_code}: {detail}",
                status_code=response.status_code,
            )
        try:
            return response.json()
        except ValueError as exc:
            raise WeatherXMError("WeatherXM API returned a non-JSON body") from exc


def _error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:300] or response.reason_phrase
    if isinstance(payload, dict):
        message = payload.get("message") or payload.get("error")
        if isinstance(message, str):
            return message
    return response.text[:300] or response.reason_phrase
