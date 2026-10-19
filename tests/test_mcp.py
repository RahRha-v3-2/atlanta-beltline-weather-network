import json
from io import StringIO

from ingest.models import TrailObservation
from ingest.store import MemoryStore
from mcp.server import McpServer, get_trail_conditions, serve


def test_handshake_and_empty_trail_conditions():
    server = McpServer(MemoryStore())
    init = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
        }
    )
    assert init["result"]["serverInfo"]["name"] == "beltline-telemetry"
    assert init["result"]["protocolVersion"] == "2024-11-05"

    listed = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert [tool["name"] for tool in listed["result"]["tools"]] == ["get_trail_conditions"]

    assert server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None

    called = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "get_trail_conditions", "arguments": {"segment": "eastside"}},
        }
    )
    assert called["result"]["isError"] is False
    body = json.loads(called["result"]["content"][0]["text"])
    assert body["live_data"] is False
    assert body["observations"] == []
    assert body["status"] == "proposal"
    assert "about 5" in body["summary"]


def test_unknown_segment_is_a_tool_error():
    server = McpServer(MemoryStore())
    called = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "get_trail_conditions", "arguments": {"segment": "midtown"}},
        }
    )
    assert called["result"]["isError"] is True


def test_tagged_reading_is_returned_and_unassigned_is_not_called_trail_data():
    store = MemoryStore()
    store.save(
        TrailObservation(
            station_id="east-1",
            observed_at="2026-10-18T16:00:00Z",
            segment="eastside",
            temperature_c=30,
            wind_speed_m_s=5,
            precipitation_rate_mm_h=1.5,
        )
    )
    store.save(
        TrailObservation(
            station_id="other-1",
            observed_at="2026-10-18T16:00:00Z",
            temperature_c=10,
        )
    )
    east = get_trail_conditions("eastside", store)
    west = get_trail_conditions("westside", store)
    assert east["live_data"] is True
    assert east["observations"][0]["station_id"] == "east-1"
    assert "30.0" in east["summary"]
    assert east["unassigned_station_count"] == 1
    assert "not issued" in east["advisory"]
    assert west["live_data"] is False


def test_stdio_round_trip():
    incoming = StringIO(
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}) + "\n"
        "not-json\n"
    )
    outgoing = StringIO()
    serve(stdin=incoming, stdout=outgoing, store=MemoryStore())
    lines = [json.loads(line) for line in outgoing.getvalue().splitlines()]
    assert lines[0]["result"] == {}
    assert lines[1]["error"]["code"] == -32700
