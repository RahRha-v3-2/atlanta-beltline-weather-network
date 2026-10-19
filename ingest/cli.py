"""Small CLI for pulling WeatherXM station observations.

Examples:

    python -m ingest latest --station-id <uuid>
    python -m ingest history --station-id <uuid> --date 2026-10-18
    python -m ingest pull --write
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from typing import TextIO

from ingest.client import WeatherXMClient, WeatherXMError
from ingest.config import ConfigError, Settings
from ingest.models import SEGMENTS, TrailObservation, to_trail_observation
from ingest.qod import qod_accepts
from ingest.store import MemoryStore, PostgresStore, Store


def build_client(settings: Settings) -> WeatherXMClient:
    return WeatherXMClient(api_key=settings.require_api_key(), base_url=settings.base_url)


def main(
    argv: list[str] | None = None,
    *,
    client: WeatherXMClient | None = None,
    store: Store | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        settings = Settings.from_env()
        if args.segment:
            settings = Settings(
                api_key=settings.api_key,
                base_url=settings.base_url,
                station_ids=settings.station_ids,
                segment=args.segment,
                database_url=settings.database_url,
                qod_min_score=settings.qod_min_score,
            )
        if args.qod_min is not None:
            settings = Settings(
                api_key=settings.api_key,
                base_url=settings.base_url,
                station_ids=settings.station_ids,
                segment=settings.segment,
                database_url=settings.database_url,
                qod_min_score=args.qod_min,
            )
        _validate_segment(settings.segment)
        if args.command == "latest":
            return _latest(args, settings, client, out, err)
        if args.command == "history":
            return _history(args, settings, client, out, err)
        return _pull(args, settings, client, store, out, err)
    except (ConfigError, WeatherXMError, ValueError) as exc:
        print(str(exc), file=err)
        return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ingest",
        description=(
            "Pull station observations from the WeatherXM Pro API. "
            "Station IDs are explicit. This tool does not search the map for BeltLine stations."
        ),
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--segment",
        choices=sorted(SEGMENTS),
        help="Label stored with the reading. Omit unless this is a known host site.",
    )
    common.add_argument(
        "--qod-min",
        type=float,
        default=None,
        help="Override QOD_MIN_SCORE for this run (0 to 1).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    latest = sub.add_parser(
        "latest",
        parents=[common],
        help="Print the latest observation for one station",
    )
    latest.add_argument("--station-id", required=True)

    history = sub.add_parser(
        "history",
        parents=[common],
        help="Print observations for one UTC date or a range",
    )
    history.add_argument("--station-id", required=True)
    history.add_argument("--date", dest="on_date", help="UTC date YYYY-MM-DD")
    history.add_argument("--start", help="UTC range start YYYY-MM-DD")
    history.add_argument("--end", help="UTC range end YYYY-MM-DD")

    pull = sub.add_parser(
        "pull",
        parents=[common],
        help="Pull latest observations for configured station IDs",
    )
    pull.add_argument(
        "--station-id",
        action="append",
        dest="station_ids",
        default=None,
        help="Repeatable. Defaults to WEATHERXM_STATION_IDS.",
    )
    pull.add_argument(
        "--write",
        action="store_true",
        help="Persist accepted observations when DATABASE_URL is set.",
    )
    return parser


def _latest(
    args: argparse.Namespace,
    settings: Settings,
    client: WeatherXMClient | None,
    out: TextIO,
    err: TextIO,
) -> int:
    owned = client is None
    wxm = client or build_client(settings)
    try:
        reading = wxm.latest(args.station_id)
        row = to_trail_observation(reading, segment=settings.segment)
        if not qod_accepts(row.qod_score, settings.qod_min_score):
            print(
                f"dropped {row.station_id}: qod {row.qod_score} is below {settings.qod_min_score}",
                file=err,
            )
            return 3
        json.dump(row.as_dict(), out, indent=2)
        out.write("\n")
        return 0
    finally:
        if owned:
            wxm.close()


def _history(
    args: argparse.Namespace,
    settings: Settings,
    client: WeatherXMClient | None,
    out: TextIO,
    err: TextIO,
) -> int:
    del err
    _validate_history_window(args.on_date, args.start, args.end)
    owned = client is None
    wxm = client or build_client(settings)
    try:
        observations = wxm.history(
            args.station_id,
            on_date=args.on_date,
            start=args.start,
            end=args.end,
        )
        json.dump([obs.__dict__ for obs in observations], out, indent=2)
        out.write("\n")
        return 0
    finally:
        if owned:
            wxm.close()


def _pull(
    args: argparse.Namespace,
    settings: Settings,
    client: WeatherXMClient | None,
    store: Store | None,
    out: TextIO,
    err: TextIO,
) -> int:
    station_ids = tuple(args.station_ids or settings.station_ids)
    if not station_ids:
        print(
            "No station IDs configured. Set WEATHERXM_STATION_IDS or pass --station-id. "
            "Phase 1 proposes about 5 stations; none are deployed, so this command "
            "will not invent IDs or search a bounding box.",
            file=err,
        )
        return 2
    owned = client is None
    wxm = client or build_client(settings)
    try:
        accepted: list[dict[str, object]] = []
        dropped: list[dict[str, object]] = []
        pending: list[TrailObservation] = []
        for station_id in station_ids:
            reading = wxm.latest(station_id)
            row = to_trail_observation(reading, segment=settings.segment)
            if not qod_accepts(row.qod_score, settings.qod_min_score):
                dropped.append({"station_id": station_id, "qod_score": row.qod_score})
                continue
            accepted.append(row.as_dict())
            pending.append(row)
        persist = bool(args.write and (store is not None or settings.database_url))
        if persist:
            destination = _destination(settings, store)
            for row in pending:
                destination.save(row)
        elif args.write:
            print("--write was set but DATABASE_URL is empty, so nothing was stored.", file=err)
        json.dump(
            {
                "written": len(accepted) if persist else 0,
                "observations": accepted,
                "dropped": dropped,
            },
            out,
            indent=2,
        )
        out.write("\n")
        return 0
    finally:
        if owned:
            wxm.close()


def _destination(settings: Settings, store: Store | None) -> Store:
    if store is not None:
        return store
    if settings.database_url:
        return PostgresStore(settings.database_url)
    return MemoryStore()


def _validate_segment(segment: str | None) -> None:
    if segment is not None and segment not in SEGMENTS:
        raise ConfigError(f"segment must be one of {sorted(SEGMENTS)}")


def _validate_history_window(on_date: str | None, start: str | None, end: str | None) -> None:
    if on_date:
        _parse_day(on_date)
        return
    if not start or not end:
        raise ConfigError("history requires --date, or both --start and --end (YYYY-MM-DD, UTC)")
    start_day = _parse_day(start)
    end_day = _parse_day(end)
    if end_day < start_day:
        raise ConfigError("--end must be on or after --start")
    if end_day - start_day > timedelta(days=7):
        raise ConfigError("WeatherXM Pro history range cannot be greater than 7 days")


def _parse_day(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ConfigError(f"Invalid date {value!r}; use YYYY-MM-DD") from exc
