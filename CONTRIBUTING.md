# Contributing

This repository is an early prototype for a proposed pilot. Contributions should keep that description accurate.

## Honesty

- Do not state that stations are deployed on the Atlanta BeltLine, or that Atlanta Beltline, Inc., the City of Atlanta, or the BeltLine app has agreed to anything. None of those is true.
- Do not add station counts other than the phase 1 proposal of about 5 stations.
- Do not seed fake observations, customers, logos, or uptime. 99.9% uptime is a design target only.
- Do not tag a WeatherXM station as `eastside` or `westside` unless it is a known host site for this pilot.
- Do not commit API keys, `.env`, wallet addresses, or host-site contact details.

## Local setup

Python 3.12 is required.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
pytest
ruff check .
```

The API runs without Postgres:

```bash
uvicorn api.main:app --reload
```

`GET /health`, `GET /stations`, and `GET /observations/latest` respond. The station and observation lists are empty until you ingest real station IDs.

Ingest needs a WeatherXM Pro API key in the environment:

```bash
export WEATHERXM_API_KEY=...
python -m ingest latest --station-id <weatherxm-station-uuid>
```

`--segment` is optional and should stay unset for stations that are not part of the pilot.

Postgres, when you want it:

```bash
docker compose up --build db api
```

The database password in `docker-compose.yml` is a local default, not a credential for any shared environment.

## Tests

CI runs `ruff check` and `pytest` on Python 3.12. Tests use an in-memory store and a mocked HTTP client. They do not call WeatherXM and they do not require TimescaleDB.

## License

Contributions are under Apache-2.0. WeatherXM observation data remains under WeatherXM's terms even when a copy is stored here. Do not mark WeatherXM rows as CC BY 4.0. That license is reserved for this project's own air-quality readings, which are not collected yet.
