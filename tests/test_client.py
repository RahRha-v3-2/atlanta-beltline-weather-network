import json

import httpx

from ingest.client import WeatherXMClient, WeatherXMError
from ingest.models import parse_history_observations

STATION = "3355b780-438d-11ef-8e8d-b55568dc8e66"

LATEST_BODY = {
    "observation": {
        "timestamp": "2026-10-18T15:42:20.248Z",
        "temperature": 21.4,
        "feels_like": 21.0,
        "dew_point": 14.2,
        "humidity": 64,
        "precipitation_rate": 0,
        "precipitation_accumulated": 12.5,
        "wind_speed": 1.2,
        "wind_gust": 2.4,
        "wind_direction": 180,
        "uv_index": 3,
        "pressure": 1012.4,
        "solar_irradiance": 420.0,
        "icon": "partly-cloudy-day",
    },
    "health": {
        "timestamp": "2026-10-18T00:00:00Z",
        "data_quality": {"score": 0.95},
        "location_quality": {"score": 1, "reason": None},
    },
    "location": {"lat": 33.77, "lon": -84.36, "elevation": 300},
}


def _client(handler) -> WeatherXMClient:
    http = httpx.Client(
        base_url="https://pro.weatherxm.com/api/v1",
        transport=httpx.MockTransport(handler),
        headers={"X-API-KEY": "test-key"},
    )
    return WeatherXMClient("test-key", http=http)


def test_latest_uses_pro_path_and_api_key_header():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["key"] = request.headers["X-API-KEY"]
        return httpx.Response(200, json=LATEST_BODY)

    reading = _client(handler).latest(STATION)

    assert seen["path"] == f"/api/v1/stations/{STATION}/latest"
    assert seen["key"] == "test-key"
    assert reading.observation.temperature == 21.4
    assert reading.observation.wind_direction == 180
    assert reading.health is not None
    assert reading.health.data_quality_score == 0.95
    assert reading.location is not None
    assert reading.location.lat == 33.77


def test_latest_fills_qod_from_health_endpoint_when_latest_omits_it():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path.endswith("/health"):
            health = {"data_quality": {"score": 0.8}, "timestamp": "2026-10-18T00:00:00Z"}
            return httpx.Response(200, json={"health": health})
        body = json.loads(json.dumps(LATEST_BODY))
        body["health"] = None
        return httpx.Response(200, json=body)

    reading = _client(handler).latest(STATION)

    assert calls == [
        f"/api/v1/stations/{STATION}/latest",
        f"/api/v1/stations/{STATION}/health",
    ]
    assert reading.health is not None
    assert reading.health.data_quality_score == 0.8


def test_history_sends_date_and_parses_observations():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["date"] == "2026-10-18"
        return httpx.Response(
            200,
            json={"date": "2026-10-18", "observations": [LATEST_BODY["observation"]]},
        )

    rows = _client(handler).history(STATION, on_date="2026-10-18")
    assert len(rows) == 1
    assert rows[0].precipitation_accumulated == 12.5


def test_history_range_accepts_a_list_of_day_blocks():
    payload = [
        {"date": "2026-10-17", "observations": [LATEST_BODY["observation"]]},
        {"date": "2026-10-18", "observations": []},
    ]
    rows = parse_history_observations(payload)
    assert len(rows) == 1


def test_missing_api_key_fails_before_a_request():
    try:
        WeatherXMClient("  ")
    except WeatherXMError as exc:
        assert "X-API-KEY" in str(exc)
    else:
        raise AssertionError("expected WeatherXMError")


def test_http_error_includes_weatherxm_message():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "API key is missing"})

    try:
        _client(handler).latest(STATION)
    except WeatherXMError as exc:
        assert exc.status_code == 401
        assert "API key is missing" in str(exc)
    else:
        raise AssertionError("expected WeatherXMError")
