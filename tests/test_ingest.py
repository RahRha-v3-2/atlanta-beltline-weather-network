import json
from io import StringIO

import pytest

from ingest.cli import main
from ingest.models import (
    Health,
    LatestReading,
    Location,
    Observation,
    TrailObservation,
    to_trail_observation,
)
from ingest.qod import qod_accepts
from ingest.store import MemoryStore


def _reading(station_id: str = "station-a", score: float | None = 0.9) -> LatestReading:
    return LatestReading(
        station_id=station_id,
        observation=Observation(
            timestamp="2026-10-18T15:00:00Z",
            temperature=28.0,
            humidity=55,
            precipitation_rate=0.2,
            wind_speed=3.5,
            wind_direction=90,
            pressure=1008,
        ),
        health=None if score is None else Health(data_quality_score=score),
        location=Location(lat=33.76, lon=-84.37, elevation=290),
    )


class FakeClient:
    def __init__(self, readings: dict[str, LatestReading]):
        self.readings = readings
        self.closed = False

    def latest(self, station_id: str) -> LatestReading:
        return self.readings[station_id]

    def close(self) -> None:
        self.closed = True


def test_qod_gate():
    assert qod_accepts(None, 0) is True
    assert qod_accepts(0.2, 0) is True
    assert qod_accepts(None, 0.5) is False
    assert qod_accepts(0.49, 0.5) is False
    assert qod_accepts(0.5, 0.5) is True
    with pytest.raises(ValueError):
        qod_accepts(1, 1.5)


def test_segment_must_be_known():
    with pytest.raises(ValueError):
        to_trail_observation(_reading(), segment="beltline")


def test_cli_requires_api_key(monkeypatch):
    monkeypatch.delenv("WEATHERXM_API_KEY", raising=False)
    err = StringIO()
    code = main(["latest", "--station-id", "abc"], stderr=err)
    assert code == 2
    assert "WEATHERXM_API_KEY" in err.getvalue()


def test_pull_refuses_to_invent_station_ids(monkeypatch):
    monkeypatch.setenv("WEATHERXM_API_KEY", "test-key")
    monkeypatch.delenv("WEATHERXM_STATION_IDS", raising=False)
    err = StringIO()
    code = main(["pull"], stderr=err)
    assert code == 2
    assert "about 5" in err.getvalue()


def test_pull_filters_qod_and_can_write(monkeypatch):
    monkeypatch.setenv("WEATHERXM_API_KEY", "test-key")
    monkeypatch.setenv("QOD_MIN_SCORE", "0.8")
    store = MemoryStore()
    client = FakeClient(
        {
            "good": _reading("good", 0.91),
            "poor": _reading("poor", 0.2),
        }
    )
    out = StringIO()
    code = main(
        [
            "pull",
            "--station-id",
            "good",
            "--station-id",
            "poor",
            "--write",
            "--segment",
            "eastside",
        ],
        client=client,
        store=store,
        stdout=out,
    )
    payload = json.loads(out.getvalue())
    assert code == 0
    assert payload["written"] == 1
    assert payload["dropped"] == [{"station_id": "poor", "qod_score": 0.2}]
    stored = store.latest_observations(segment="eastside")
    assert [row.station_id for row in stored] == ["good"]
    assert stored[0].temperature_c == 28.0
    assert stored[0].source == "weatherxm"
    assert client.closed is False


def test_memory_store_keeps_segment_when_a_later_reading_omits_it():
    store = MemoryStore()
    store.save(
        TrailObservation(
            station_id="s",
            observed_at="2026-10-18T12:00:00Z",
            segment="eastside",
            station_name="Host",
            temperature_c=20,
        )
    )
    store.save(
        TrailObservation(
            station_id="s",
            observed_at="2026-10-18T18:00:00Z",
            temperature_c=22,
        )
    )
    latest = store.latest_observations(segment="eastside")
    assert len(latest) == 1
    assert latest[0].temperature_c == 22
    assert latest[0].station_name == "Host"


def test_memory_store_keeps_newest_reading():
    store = MemoryStore()
    older = TrailObservation(
        station_id="s",
        observed_at="2026-10-18T12:00:00+00:00",
        temperature_c=20,
        segment="eastside",
    )
    newer = TrailObservation(
        station_id="s",
        observed_at="2026-10-18T18:00:00Z",
        temperature_c=25,
        segment="eastside",
    )
    store.save(older)
    store.save(newer)
    latest = store.latest_observations()
    assert len(latest) == 1
    assert latest[0].temperature_c == 25


def test_history_rejects_ranges_over_seven_days(monkeypatch):
    monkeypatch.setenv("WEATHERXM_API_KEY", "test-key")
    err = StringIO()
    code = main(
        ["history", "--station-id", "abc", "--start", "2026-10-01", "--end", "2026-10-20"],
        stderr=err,
    )
    assert code == 2
    assert "7 days" in err.getvalue()
