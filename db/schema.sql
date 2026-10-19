-- Atlanta BeltLine telemetry prototype schema.
-- TimescaleDB on PostgreSQL. The docker-compose database image provides the extension.
-- This file creates empty tables. It does not seed stations or observations.
--
-- Phase 1 is a proposal: about 5 WeatherXM stations on consenting private host
-- sites next to the Eastside Trail. No row in this schema is a BeltLine deployment
-- until an operator ingests a real station and sets segment explicitly.

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS stations (
    id text PRIMARY KEY,
    name text,
    cell_index text,
    -- eastside or westside, and only when an operator sets it. NULL means unassigned.
    segment text,
    latitude double precision,
    longitude double precision,
    elevation_m double precision,
    created_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT stations_segment_chk CHECK (
        segment IS NULL OR segment IN ('eastside', 'westside')
    )
);

-- WeatherXM-verified observations. source stays 'weatherxm'.
-- Republishing these readings is still subject to WeatherXM's terms.
CREATE TABLE IF NOT EXISTS observations (
    station_id text NOT NULL REFERENCES stations (id),
    observed_at timestamptz NOT NULL,
    temperature_c double precision,
    feels_like_c double precision,
    dew_point_c double precision,
    humidity_pct double precision,
    precipitation_rate_mm_h double precision,
    precipitation_accumulated_mm double precision,
    wind_speed_m_s double precision,
    wind_gust_m_s double precision,
    wind_direction_deg integer,
    uv_index double precision,
    pressure_hpa double precision,
    solar_irradiance_w_m2 double precision,
    icon text,
    qod_score double precision,
    source text NOT NULL DEFAULT 'weatherxm',
    license text NOT NULL DEFAULT 'WeatherXM terms',
    ingested_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (station_id, observed_at),
    CONSTRAINT observations_source_chk CHECK (source = 'weatherxm')
);

SELECT create_hypertable('observations', 'observed_at', if_not_exists => TRUE);

-- Proposed co-located air-quality sensors. Not WeatherXM data, not collected yet.
-- Kept in a separate table so it cannot be mixed into WeatherXM observations.
CREATE TABLE IF NOT EXISTS air_quality_observations (
    sensor_id text NOT NULL,
    observed_at timestamptz NOT NULL,
    pm2_5 double precision,
    pm10 double precision,
    aqi integer,
    source text NOT NULL DEFAULT 'colocated_sensor',
    license text NOT NULL DEFAULT 'CC BY 4.0',
    ingested_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (sensor_id, observed_at),
    CONSTRAINT air_quality_source_chk CHECK (source = 'colocated_sensor')
);
