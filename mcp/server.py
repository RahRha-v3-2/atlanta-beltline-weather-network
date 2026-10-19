"""Newline-delimited JSON-RPC MCP server.

Speaks protocol version 2024-11-05 over stdio. One tool is exposed:
`get_trail_conditions`. The tool reads the local observation store and does
not call WeatherXM, and it does not invent readings when the store is empty.

    python -m mcp.server
"""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from ingest.models import SEGMENTS, TrailObservation
from ingest.store import Store, store_from_env

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "beltline-telemetry"
SERVER_VERSION = "0.1.0"

TOOL = {
    "name": "get_trail_conditions",
    "description": (
        "Return the latest stored WeatherXM readings for a proposed Atlanta BeltLine "
        "segment. Phase 1 targets the Eastside Trail only. If no stations have been "
        "ingested, the tool says so. It does not invent weather."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "segment": {
                "type": "string",
                "enum": ["eastside", "westside", "corridor"],
                "description": (
                    "eastside is the phase 1 proposal. westside is a later expansion. "
                    "corridor returns readings explicitly tagged to either segment."
                ),
            }
        },
        "additionalProperties": False,
    },
}


class McpServer:
    def __init__(self, store: Store | None = None) -> None:
        self.store = store or store_from_env()

    def handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        if message.get("jsonrpc") != "2.0" or "method" not in message:
            return _error(message.get("id"), -32600, "Invalid Request")
        method = message["method"]
        request_id = message.get("id")
        if request_id is None and method.startswith("notifications/"):
            return None
        if method == "initialize":
            return _result(
                request_id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                },
            )
        if method == "ping":
            return _result(request_id, {})
        if method == "tools/list":
            return _result(request_id, {"tools": [TOOL]})
        if method == "tools/call":
            return self._call(request_id, message.get("params") or {})
        return _error(request_id, -32601, f"Method not found: {method}")

    def _call(self, request_id: Any, params: Any) -> dict[str, Any]:
        if not isinstance(params, dict):
            return _error(request_id, -32602, "Invalid params")
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name != "get_trail_conditions":
            return _tool_error(request_id, f"Unknown tool: {name}")
        if not isinstance(arguments, dict):
            return _tool_error(request_id, "arguments must be an object")
        segment = arguments.get("segment", "eastside")
        if not isinstance(segment, str):
            return _tool_error(request_id, "segment must be a string")
        try:
            payload = get_trail_conditions(segment, self.store)
        except ValueError as exc:
            return _tool_error(request_id, str(exc))
        return _result(
            request_id,
            {
                "content": [{"type": "text", "text": json.dumps(payload)}],
                "isError": False,
            },
        )


def get_trail_conditions(segment: str, store: Store) -> dict[str, Any]:
    """Summarize stored readings for a segment. Empty means no live corridor data."""

    normalized = segment.strip().lower()
    if normalized not in SEGMENTS | {"corridor"}:
        raise ValueError("segment must be eastside, westside, or corridor")
    stored = store.latest_observations()
    if normalized == "corridor":
        matched = [row for row in stored if row.segment in SEGMENTS]
    else:
        matched = [row for row in stored if row.segment == normalized]
    unassigned = [row for row in stored if row.segment not in SEGMENTS]
    if not matched:
        scope = (
            "the proposed corridor"
            if normalized == "corridor"
            else f"the proposed {normalized} segment"
        )
        return {
            "segment": normalized,
            "status": "proposal",
            "live_data": False,
            "summary": (
                f"No WeatherXM stations tagged to {scope} are in the store. "
                "Phase 1 proposes about 5 stations on consenting private host sites "
                "next to the Eastside Trail. No deployment exists, and there is no "
                "agreement with Atlanta Beltline, Inc., the City of Atlanta, or the "
                "BeltLine app. This is not a forecast and no alert is in effect."
            ),
            "observations": [],
            "unassigned_station_count": len(unassigned),
        }
    return {
        "segment": normalized,
        "status": "proposal",
        "live_data": True,
        "summary": _summary(normalized, matched),
        "observations": [row.as_dict() for row in matched],
        "unassigned_station_count": len(unassigned),
        "advisory": (
            "Values are ingested station readings for explicitly tagged host sites. "
            "They are not an official BeltLine product. Heat, flood, and wind alerts "
            "are a later milestone and are not issued here."
        ),
    }


def _summary(segment: str, rows: list[TrailObservation]) -> str:
    temps = [row.temperature_c for row in rows if row.temperature_c is not None]
    winds = [row.wind_speed_m_s for row in rows if row.wind_speed_m_s is not None]
    rain = [
        row.precipitation_rate_mm_h
        for row in rows
        if row.precipitation_rate_mm_h is not None
    ]
    parts = [
        f"{len(rows)} tagged station reading(s) for {segment}.",
    ]
    if temps:
        parts.append(f"Temperature {min(temps):.1f} to {max(temps):.1f} °C.")
    if winds:
        parts.append(f"Highest wind speed {max(winds):.1f} m/s.")
    if rain:
        parts.append(f"Highest precipitation rate {max(rain):.2f} mm/h.")
    return " ".join(parts)


def serve(
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    store: Store | None = None,
) -> None:
    incoming = stdin or sys.stdin
    outgoing = stdout or sys.stdout
    server = McpServer(store)
    for line in incoming:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            _write(outgoing, _error(None, -32700, "Parse error"))
            continue
        if not isinstance(message, dict):
            _write(outgoing, _error(None, -32600, "Invalid Request"))
            continue
        response = server.handle(message)
        if response is not None:
            _write(outgoing, response)


def main() -> int:
    serve()
    return 0


def _result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _tool_error(request_id: Any, message: str) -> dict[str, Any]:
    return _result(
        request_id,
        {"content": [{"type": "text", "text": message}], "isError": True},
    )


def _write(outgoing: TextIO, payload: dict[str, Any]) -> None:
    outgoing.write(json.dumps(payload) + "\n")
    outgoing.flush()
