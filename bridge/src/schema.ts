import type { StreamPath } from "./streams.js";

export const SCHEMA_ID = "open-depin-telemetry/v1" as const;

export type NetworkId = "weatherxm" | "geodnet" | "wingbits" | "helium" | "beltline-air-quality";

export type AdapterStatus = "implemented" | "stub" | "sample";

export type TrailSegment = "eastside" | "westside";

export interface WeatherFields {
  temperatureC: number | null;
  feelsLikeC: number | null;
  dewPointC: number | null;
  humidityPct: number | null;
  precipitationRateMmH: number | null;
  precipitationAccumulatedMm: number | null;
  windSpeedMs: number | null;
  windGustMs: number | null;
  windDirectionDeg: number | null;
  uvIndex: number | null;
  pressureHpa: number | null;
  solarIrradianceWm2: number | null;
  icon: string | null;
  qodScore: number | null;
}

export interface StationHealth {
  online: boolean | null;
  lastSeenAt: string | null;
  detail: string | null;
}

export interface AirQualityFields {
  pm25: number | null;
  pm10: number | null;
  aqi: number | null;
}

/**
 * One normalized reading. `publishable` is a license decision, not a claim
 * that a Streamr stream exists.
 */
export interface TelemetryMessage {
  schema: typeof SCHEMA_ID;
  observedAt: string;
  ingestedAt: string;
  source: {
    network: NetworkId;
    stationId: string;
    adapter: string;
    adapterStatus: AdapterStatus;
  };
  stream: StreamPath;
  segment: TrailSegment | null;
  location: {
    latitude: number | null;
    longitude: number | null;
    elevationM: number | null;
  } | null;
  weather: WeatherFields | null;
  health: StationHealth | null;
  airQuality: AirQualityFields | null;
  license: string;
  publishable: boolean;
  publishBlockReason: string | null;
  sample: boolean;
}

export function emptyWeather(): WeatherFields {
  return {
    temperatureC: null,
    feelsLikeC: null,
    dewPointC: null,
    humidityPct: null,
    precipitationRateMmH: null,
    precipitationAccumulatedMm: null,
    windSpeedMs: null,
    windGustMs: null,
    windDirectionDeg: null,
    uvIndex: null,
    pressureHpa: null,
    solarIrradianceWm2: null,
    icon: null,
    qodScore: null,
  };
}

export const WEATHERXM_LICENSE = "WeatherXM terms";

export const WEATHERXM_BLOCK_REASON =
  "WeatherXM observations stay under WeatherXM's terms. Public publish is off until STREAMR_ALLOW_PUBLIC_WEATHERXM=1, which records that the operator checked those terms for this use.";
