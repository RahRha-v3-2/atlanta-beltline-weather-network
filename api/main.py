"""FastAPI surface for the proposed BeltLine telemetry pilot.

Endpoints:
- GET /health
- GET /stations
- GET /observations/latest

The store starts empty. An empty list means no observations have been ingested.
"""

from __future__ import annotations

from typing import Any

import uvicorn
from fastapi import FastAPI, Query

from ingest.store import Store, store_from_env

EMPTY_NOTE = (
    "No stations are stored. This service is an early prototype for a proposed pilot. "
    "Phase 1 proposes about 5 WeatherXM stations on consenting private host sites next "
    "to the Eastside Trail. Nothing is deployed, and there is no agreement with "
    "Atlanta Beltline, Inc., the City of Atlanta, or the BeltLine app."
)


def create_app(store: Store | None = None) -> FastAPI:
    app = FastAPI(
        title="Atlanta BeltLine Telemetry API",
        version="0.1.0",
        description=(
            "Early prototype for a proposed WeatherXM pilot along the Atlanta BeltLine. "
            "No stations are deployed. Empty responses are empty, not sample weather."
        ),
    )
    app.state.store = store or store_from_env()

    @app.get("/health")
    def health() -> dict[str, Any]:
        backend: Store = app.state.store
        database_ok = backend.ping()
        return {
            "status": "ok" if database_ok else "degraded",
            "service": "beltline-telemetry-api",
            "version": "0.1.0",
            "phase": "proposal",
            "database": backend.kind(),
            "database_ok": database_ok,
            "note": "99.9% uptime is a design target, not a measured figure.",
        }

    @app.get("/stations")
    def stations(
        segment: str | None = Query(default=None, pattern="^(eastside|westside)$"),
    ) -> dict[str, Any]:
        rows = app.state.store.list_stations(segment)
        body: dict[str, Any] = {"stations": rows, "count": len(rows)}
        if not rows:
            body["note"] = EMPTY_NOTE
        return body

    @app.get("/observations/latest")
    def latest(
        segment: str | None = Query(default=None, pattern="^(eastside|westside)$"),
    ) -> dict[str, Any]:
        rows = app.state.store.latest_observations(segment)
        body: dict[str, Any] = {
            "observations": [row.as_dict() for row in rows],
            "count": len(rows),
            "status": "proposal",
        }
        if not rows:
            body["note"] = EMPTY_NOTE
        else:
            body["note"] = (
                "These are ingested WeatherXM station readings. "
                "They are not a corridor forecast, and heat, flood, and wind alerts "
                "are not issued by this prototype."
            )
        return body

    return app


app = create_app()


def main() -> None:
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
