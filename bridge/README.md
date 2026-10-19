# Open DePIN Telemetry Bridge

Early prototype of the Streamr publisher for this repo. **No Streamr stream has been created.** A Streamr Data Fund Quick Response application (Integration category, proposed $4,000) has been submitted. It has not been awarded. There is no agreement with Streamr, Atlanta Beltline, Inc., or the City of Atlanta.

The package is Apache-2.0 and targets Node 20. It uses `@streamr/sdk` 103.4.0.

## What runs today

Milestone 1 of that application is the bridge core plus a WeatherXM stream. This tree has the core and a WeatherXM adapter. The default mode is a dry run: it logs messages and does not publish them. A live WeatherXM stream is not running.

| Piece | State |
| --- | --- |
| Adapter interface, normalized message, publisher | In this package |
| WeatherXM, from `GET /observations/latest` and/or the WeatherXM Pro API | Implemented. Public publish stays off until a license flag is set |
| `beltline/air-quality`, `fleet/geodnet-status`, `fleet/wingbits`, `fleet/helium` | Stubs. They return no messages. GEODNET is station health only; RTK corrections are out of scope |
| Docker image and compose service | Present, default dry run. Not a claim that it has been run on a Raspberry Pi |
| Dashboard | Not in this package |

## Quick start

From `bridge/`:

```bash
npm ci
npm test
npm run dev -- --once --sample
```

`--sample` prints one JSON line for `sample-not-a-station`. That id is not a weather station. `published` is false.

A dry run against this repo's API, after the API is up and has ingested rows:

```bash
export BELTLINE_API_URL=http://127.0.0.1:8000
export STREAMR_DRY_RUN=1
npm run dev -- --once
```

An empty API logs `messages=0`. It does not invent readings.

WeatherXM Pro, with explicit station ids only:

```bash
export WEATHERXM_API_KEY=...   # not committed
export WEATHERXM_STATION_IDS=<uuid>
export WEATHERXM_SOURCE=pro
export STREAMR_DRY_RUN=1
npm run dev -- --once
```

`--segment eastside` is only for a host site you actually have. Leave it unset otherwise. Untagged readings are not written to the `beltline/weather` path.

## Stream names

`STREAMR_STREAM_ID_PREFIX` plus a fixed path. The dry-run prefix `dry-run/open-depin-telemetry` is a placeholder, not a Streamr stream id. A real id looks like `/open-depin-telemetry/...` or `0x<your-address>/open-depin-telemetry/...`, and only after someone creates it.

| Path | Adapter |
| --- | --- |
| `fleet/weatherxm` | WeatherXM readings |
| `beltline/weather` | The same reading, only when `segment` is `eastside` or `westside` |
| `beltline/air-quality` | Stub |
| `fleet/geodnet-status` | Stub. Health only, no RTK corrections |
| `fleet/wingbits` | Stub |
| `fleet/helium` | Stub |

`npm run create-streams -- --dry-run` prints those six ids and the public-subscribe grant it would submit. It does not send a transaction.

Creating a stream, or granting public subscribe, is on-chain on Polygon and needs POL for gas. Public publish permission is not granted. The owner key can publish because it creates the stream. The first live `getOrCreateStream` can also be that create, so a live process warns before it starts. No key is stored in the repo. `STREAMR_PRIVATE_KEY` stays in the environment.

## Message schema

`schema` is `open-depin-telemetry/v1`. Fields use explicit units (`temperatureC`, `windSpeedMs`, `precipitationRateMmH`, `pressureHpa`). `license` is the source license, not a new one granted by this repo. `publishable` is false unless that source has been cleared.

WeatherXM rows keep `license: "WeatherXM terms"`. They are not published unless `STREAMR_ALLOW_PUBLIC_WEATHERXM=1`. That flag means the operator checked WeatherXM's terms for a public Streamr mirror. This package does not decide that the terms allow it.

Air-quality data, if this project later collects it, is intended for CC BY 4.0 and stays out of the WeatherXM stream. None has been collected.

## Environment

See the root `.env.example`. The ones this process reads:

| Variable | Role |
| --- | --- |
| `STREAMR_DRY_RUN` | Default `1`. `0` publishes, and requires a key and prefix |
| `STREAMR_PRIVATE_KEY` | Stream owner Ethereum key. Never commit it |
| `STREAMR_STREAM_ID_PREFIX` | Required for a live run |
| `STREAMR_POLL_INTERVAL_MS` | Default `60000`, minimum `1000` |
| `STREAMR_ONCE` | `1` exits after one poll. `--once` does the same |
| `STREAMR_SAMPLE` | Dry-run sample payload. Refused when dry-run is off |
| `STREAMR_ALLOW_PUBLIC_WEATHERXM` | Default `0` |
| `STREAMR_ADAPTERS` | Default `weatherxm` |
| `BELTLINE_API_URL` | Local read API, no trailing path |
| `WEATHERXM_SOURCE` | `auto`, `local`, `pro`, or `both` |
| `WEATHERXM_API_KEY`, `WEATHERXM_API_BASE_URL`, `WEATHERXM_STATION_IDS`, `WEATHERXM_SEGMENT`, `QOD_MIN_SCORE` | Same WeatherXM inputs as the Python ingest |

`auto` uses the local API when `BELTLINE_API_URL` is set, the Pro API when a key and station ids are set, and both when both are set. It does not look up stations by map.

## Docker and Raspberry Pi

The image is `node:20-bookworm-slim`, which publishes `linux/amd64` and `linux/arm64`. A 64-bit Raspberry Pi can build the arm64 image. This environment has not run that build, and no Pi is part of this prototype.

```bash
docker buildx build --platform linux/arm64,linux/amd64 -t beltline-streamr-bridge bridge
```

From the repo root, the compose service is behind the `bridge` profile and defaults to a dry run against the local API:

```bash
docker compose --profile bridge up --build
```

That starts Postgres, the API, and the bridge. With an empty database the bridge logs zero messages.

## Tests

`npm test` mocks `@streamr/sdk` behind a gateway interface and mocks HTTP. It does not join Streamr and does not call WeatherXM. `npm run lint` and `npm run typecheck` are the other CI steps.
