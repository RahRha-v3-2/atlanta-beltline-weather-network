# Data model

The physical schema is `db/schema.sql`. It is applied to an empty TimescaleDB database. No seed rows are included.

WeatherXM observations and proposed air-quality readings are different tables on purpose.

## stations

One row per WeatherXM station the operator has ingested.

| Column | Meaning |
| --- | --- |
| `id` | WeatherXM station UUID. Primary key. |
| `name` | Station name when the operator or a later metadata call has one. Latest-observation responses do not include it. |
| `cell_index` | H3 cell index when known. |
| `segment` | `eastside`, `westside`, or NULL. NULL means the station is not tagged to the pilot. |
| `latitude`, `longitude`, `elevation_m` | From the Pro API location object (`lat`, `lon`, `elevation`). |
| `created_at` | Unused by the current ingest path. Reserved for the station's WeatherXM `createdAt`. |
| `updated_at` | Last upsert. |

A station inside an Atlanta bounding box is not given a segment by geography. The ingest CLI sets `segment` only from `--segment` or `WEATHERXM_SEGMENT`.

## observations

Hypertable partitioned on `observed_at`. Primary key `(station_id, observed_at)`. `source` is constrained to `weatherxm`. `license` defaults to `WeatherXM terms`, which is a pointer to WeatherXM's own terms and not a new license granted by this project.

| Column | WeatherXM JSON | Unit |
| --- | --- | --- |
| `observed_at` | `observation.timestamp` | ISO 8601 timestamp |
| `temperature_c` | `temperature` | °C |
| `feels_like_c` | `feels_like` | °C |
| `dew_point_c` | `dew_point` | °C |
| `humidity_pct` | `humidity` | % relative humidity |
| `precipitation_rate_mm_h` | `precipitation_rate` | mm/h |
| `precipitation_accumulated_mm` | `precipitation_accumulated` | mm counter |
| `wind_speed_m_s` | `wind_speed` | m/s |
| `wind_gust_m_s` | `wind_gust` | m/s |
| `wind_direction_deg` | `wind_direction` | degrees |
| `uv_index` | `uv_index` | index |
| `pressure_hpa` | `pressure` | hPa |
| `solar_irradiance_w_m2` | `solar_irradiance` | W/m² |
| `icon` | `icon` | WeatherXM icon name |
| `qod_score` | `health.data_quality.score` | 0–1 |

`precipitation_accumulated` is a counter that resets. It is stored as reported. Daily totals are not derived in this prototype. WeatherXM's field description says to sum positive differences and to treat a decrease as a reset.

`qod_score` comes from the latest payload when present, otherwise from `GET /stations/{station_id}/health`. The health block on `/latest` is marked deprecated in the Pro spec.

Rows are upserted on `(station_id, observed_at)`. A later write does not clear a station name or segment with NULL; Postgres uses `COALESCE` so an omitted label leaves the stored label in place.

## air_quality_observations

Empty. Proposed co-located sensors, not WeatherXM stations.

| Column | Meaning |
| --- | --- |
| `sensor_id` | Sensor identity, distinct from a WeatherXM station id. |
| `pm2_5`, `pm10`, `aqi` | Not collected. |
| `source` | Constrained to `colocated_sensor`. |
| `license` | Default `CC BY 4.0`, the intended license for this project's own air-quality data. |

There is no foreign key from this table to `stations`. A sensor may sit near a host site without becoming a WeatherXM observation.

## Public API shape

`GET /stations` returns id, name, segment, cell index, and coordinates.

`GET /observations/latest` returns the newest stored row per station, using the column names above (snake_case with units). `source` is `weatherxm`.

`GET /observations/latest?segment=eastside` returns only rows tagged `eastside`.

## MCP shape

`get_trail_conditions` returns JSON text:

- `live_data: false` and an empty `observations` array when nothing is tagged to the requested segment.
- `live_data: true` only when at least one stored row has `segment` of `eastside` or `westside`.
- `unassigned_station_count` for ingested rows that have no segment. Those rows are not described as trail conditions.
- `status: "proposal"` in either case.

`corridor` is a query over both tags. It is not a station segment and it does not mean the 22-mile loop is instrumented.
