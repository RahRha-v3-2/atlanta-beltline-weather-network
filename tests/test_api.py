from fastapi.testclient import TestClient

from api.main import create_app
from ingest.models import TrailObservation
from ingest.store import MemoryStore


def _client(store: MemoryStore | None = None) -> TestClient:
    return TestClient(create_app(store or MemoryStore()))


def test_health_is_a_proposal_not_an_sla():
    body = _client().get("/health").json()
    assert body["status"] == "ok"
    assert body["phase"] == "proposal"
    assert body["database"] == "memory"
    assert "design target" in body["note"]
    assert "99.9%" in body["note"]


def test_empty_stations_and_observations_do_not_invent_data():
    client = _client()
    stations = client.get("/stations")
    latest = client.get("/observations/latest")
    assert stations.status_code == 200
    assert stations.json()["stations"] == []
    assert "about 5" in stations.json()["note"]
    assert "no agreement" in stations.json()["note"]
    assert latest.json()["observations"] == []
    assert latest.json()["status"] == "proposal"


def test_latest_returns_only_the_seeded_row():
    store = MemoryStore()
    store.save(
        TrailObservation(
            station_id="host-1",
            observed_at="2026-10-18T15:00:00Z",
            station_name="Private host",
            segment="eastside",
            latitude=33.77,
            longitude=-84.36,
            temperature_c=31.2,
            wind_speed_m_s=4.0,
            precipitation_rate_mm_h=0,
            qod_score=0.97,
        )
    )
    client = _client(store)
    east = client.get("/observations/latest", params={"segment": "eastside"}).json()
    west = client.get("/observations/latest", params={"segment": "westside"}).json()
    assert east["count"] == 1
    assert east["observations"][0]["temperature_c"] == 31.2
    assert east["observations"][0]["source"] == "weatherxm"
    assert "not issued" in east["note"]
    assert west["count"] == 0
    assert client.get("/stations").json()["count"] == 1


def test_unknown_segment_is_rejected():
    response = _client().get("/observations/latest", params={"segment": "beltline"})
    assert response.status_code == 422
