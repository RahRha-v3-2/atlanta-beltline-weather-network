# Tutorial: dry-run the telemetry bridge

This walks through the bridge that is actually in the repo. It does not create a stream, spend POL, or show live corridor data. No Streamr stream has been created. The Streamr Data Fund application has been submitted and has not been awarded.

## 1. Install and print a sample

The sample exists so the log line has a shape. The station id `sample-not-a-station` is not hardware.

```bash
cd bridge
npm ci
npm run dev -- --once --sample
```

Stdout is one JSON object. `event` is `dry-run`, `published` is false, and `message.publishable` is false. Stderr ends with `published=0`.

Leave `STREAMR_PRIVATE_KEY` unset. A dry run does not need it.

## 2. Point it at the local API

In another shell, from the repo root, start the read API if you want real ingested rows. An empty store is a valid result.

```bash
uvicorn api.main:app --port 8000
```

Then:

```bash
cd bridge
export BELTLINE_API_URL=http://127.0.0.1:8000
export STREAMR_DRY_RUN=1
npm run dev -- --once
```

`GET /observations/latest` is the only local route the bridge calls. Rows with `source: "weatherxm"` become `fleet/weatherxm` messages. A row whose `segment` is `eastside` or `westside` is also copied to `beltline/weather`. Any other segment, including null, stays off that path. The bridge will not label a station as a BeltLine host for you.

If the API has no rows, the cycle line is `messages=0`. That is the current state of this project: no station is deployed.

## 3. Read WeatherXM Pro directly

Use a station id you already have. Do not use a bounding box. The key stays in the environment.

```bash
export WEATHERXM_API_KEY=...
export WEATHERXM_STATION_IDS=<uuid>
export WEATHERXM_SOURCE=pro
export STREAMR_DRY_RUN=1
npm run dev -- --once
```

The client calls `https://pro.weatherxm.com/api/v1/stations/<id>/latest` with header `X-API-KEY`. Temperatures are Celsius, wind is meters per second, pressure is hPa, and the data-quality score is the WeatherXM 0–1 score. `QOD_MIN_SCORE` above 0 drops a weaker score and a missing score.

The message `license` is `WeatherXM terms`. `publishable` stays false. Set `STREAMR_ALLOW_PUBLIC_WEATHERXM=1` only after you have checked those terms for a public mirror. The flag does not change the license name, and a dry run still does not publish.

## 4. See the other streams without pretending they have data

```bash
npm run create-streams -- --dry-run
```

The six paths are `beltline/weather`, `beltline/air-quality`, `fleet/weatherxm`, `fleet/geodnet-status`, `fleet/wingbits`, and `fleet/helium`. Each line says `onChain: false`. GEODNET, Wingbits, Helium, and air quality are stubs: selecting them with `STREAMR_ADAPTERS` still returns no network data. GEODNET, when it is built, is station health only. RTK correction data is not part of the schema.

To create those streams later you would set `STREAMR_DRY_RUN=0`, `STREAMR_PRIVATE_KEY`, and `STREAMR_STREAM_ID_PREFIX`, then run `npm run create-streams`. That submits Polygon transactions and needs POL for gas. Do not run it until the prefix is yours and the license check for each source is done. Public subscribe would be granted. Public publish would not.

## 5. What is still unfinished

- No stream id in this repo is a stream on the Streamr network.
- The WeatherXM adapter has not been pointed at a BeltLine host site, because none is deployed.
- The non-WeatherXM adapters do not call those networks.
- There is no subscriber dashboard. `dashboard/` is still a placeholder.
- The Docker image is buildable from `node:20` for amd64 and arm64. It has not been run on a Raspberry Pi here.
