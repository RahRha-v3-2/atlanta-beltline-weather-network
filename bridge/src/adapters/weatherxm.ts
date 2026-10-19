import type { BridgeConfig, TrailSegment } from "../config.js";
import {
  SCHEMA_ID,
  WEATHERXM_BLOCK_REASON,
  WEATHERXM_LICENSE,
  emptyWeather,
  type TelemetryMessage,
  type WeatherFields,
} from "../schema.js";
import type { StreamPath } from "../streams.js";
import type { SourceAdapter } from "./types.js";

const WEATHERXM_NOTE =
  "Reads WeatherXM Pro and/or this repo's GET /observations/latest. Station ids are explicit. Untagged readings stay off beltline/weather.";

export function createWeatherXmAdapter(
  config: BridgeConfig,
  fetchImpl: typeof fetch = fetch,
): SourceAdapter {
  return {
    id: "weatherxm",
    stream: "fleet/weatherxm",
    status: "implemented",
    note: WEATHERXM_NOTE,
    poll: () => pollWeatherXm(config, fetchImpl),
  };
}

export async function pollWeatherXm(
  config: BridgeConfig,
  fetchImpl: typeof fetch,
): Promise<TelemetryMessage[]> {
  if (!config.weatherSource) return [];
  const collected: TelemetryMessage[] = [];
  if (config.weatherSource === "local" || config.weatherSource === "both") {
    collected.push(...(await pollLocal(config, fetchImpl)));
  }
  if (config.weatherSource === "pro" || config.weatherSource === "both") {
    collected.push(...(await pollPro(config, fetchImpl)));
  }
  return fanOut(dedupe(collected));
}

async function pollLocal(config: BridgeConfig, fetchImpl: typeof fetch): Promise<TelemetryMessage[]> {
  const url = `${config.beltlineApiUrl}/observations/latest`;
  const body = await getJson(fetchImpl, url);
  const rows = Array.isArray(body.observations) ? body.observations : [];
  const messages: TelemetryMessage[] = [];
  for (const row of rows) {
    if (!isRecord(row) || row.source !== "weatherxm" || typeof row.station_id !== "string") {
      continue;
    }
    if (typeof row.observed_at !== "string") continue;
    const weather = emptyWeather();
    weather.temperatureC = num(row.temperature_c);
    weather.feelsLikeC = num(row.feels_like_c);
    weather.dewPointC = num(row.dew_point_c);
    weather.humidityPct = num(row.humidity_pct);
    weather.precipitationRateMmH = num(row.precipitation_rate_mm_h);
    weather.precipitationAccumulatedMm = num(row.precipitation_accumulated_mm);
    weather.windSpeedMs = num(row.wind_speed_m_s);
    weather.windGustMs = num(row.wind_gust_m_s);
    weather.windDirectionDeg = num(row.wind_direction_deg);
    weather.uvIndex = num(row.uv_index);
    weather.pressureHpa = num(row.pressure_hpa);
    weather.solarIrradianceWm2 = num(row.solar_irradiance_w_m2);
    weather.icon = typeof row.icon === "string" ? row.icon : null;
    weather.qodScore = num(row.qod_score);
    if (!passesQod(weather.qodScore, config.qodMinScore)) continue;
    messages.push(
      messageFrom(config, {
        stationId: row.station_id,
        observedAt: row.observed_at,
        segment: segmentOf(row.segment),
        latitude: num(row.latitude),
        longitude: num(row.longitude),
        elevationM: num(row.elevation_m),
        weather,
      }),
    );
  }
  return messages;
}

async function pollPro(config: BridgeConfig, fetchImpl: typeof fetch): Promise<TelemetryMessage[]> {
  const messages: TelemetryMessage[] = [];
  for (const stationId of config.stationIds) {
    const latestUrl = `${config.weatherXmApiBaseUrl}/stations/${encodeURIComponent(stationId)}/latest`;
    const body = await getJson(fetchImpl, latestUrl, {
      headers: {
        Accept: "application/json",
        "X-API-KEY": config.weatherXmApiKey ?? "",
      },
    });
    const observation = isRecord(body.observation) ? body.observation : undefined;
    if (!observation || typeof observation.timestamp !== "string") {
      throw new Error(`WeatherXM Pro latest payload for ${stationId} has no observation timestamp.`);
    }
    const weather = weatherFromPro(observation);
    let qod = healthScore(body.health);
    if (qod === null && config.qodMinScore > 0) {
      const healthUrl = `${config.weatherXmApiBaseUrl}/stations/${encodeURIComponent(stationId)}/health`;
      const healthBody = await getJson(fetchImpl, healthUrl, {
        headers: {
          Accept: "application/json",
          "X-API-KEY": config.weatherXmApiKey ?? "",
        },
      });
      qod = healthScore(healthBody.health);
    }
    weather.qodScore = qod;
    if (!passesQod(qod, config.qodMinScore)) continue;
    const location = isRecord(body.location) ? body.location : undefined;
    messages.push(
      messageFrom(config, {
        stationId,
        observedAt: observation.timestamp,
        segment: config.segment ?? null,
        latitude: num(location?.lat),
        longitude: num(location?.lon),
        elevationM: num(location?.elevation),
        weather,
      }),
    );
  }
  return messages;
}

function messageFrom(
  config: BridgeConfig,
  input: {
    stationId: string;
    observedAt: string;
    segment: TrailSegment | null;
    latitude: number | null;
    longitude: number | null;
    elevationM: number | null;
    weather: WeatherFields;
  },
): TelemetryMessage {
  const publishable = config.allowPublicWeatherxm;
  return {
    schema: SCHEMA_ID,
    observedAt: input.observedAt,
    ingestedAt: new Date().toISOString(),
    source: {
      network: "weatherxm",
      stationId: input.stationId,
      adapter: "weatherxm",
      adapterStatus: "implemented",
    },
    stream: "fleet/weatherxm",
    segment: input.segment,
    location: {
      latitude: input.latitude,
      longitude: input.longitude,
      elevationM: input.elevationM,
    },
    weather: input.weather,
    health: null,
    airQuality: null,
    license: WEATHERXM_LICENSE,
    publishable,
    publishBlockReason: publishable ? null : WEATHERXM_BLOCK_REASON,
    sample: false,
  };
}

function fanOut(messages: TelemetryMessage[]): TelemetryMessage[] {
  const out: TelemetryMessage[] = [];
  for (const message of messages) {
    out.push(message);
    if (message.segment === "eastside" || message.segment === "westside") {
      out.push({ ...message, stream: "beltline/weather" satisfies StreamPath });
    }
  }
  return out;
}

function dedupe(messages: TelemetryMessage[]): TelemetryMessage[] {
  const byKey = new Map<string, TelemetryMessage>();
  for (const message of messages) {
    const key = `${message.source.stationId}|${message.observedAt}`;
    const current = byKey.get(key);
    if (!current) {
      byKey.set(key, message);
      continue;
    }
    byKey.set(key, {
      ...message,
      segment: current.segment ?? message.segment,
      location: message.location ?? current.location,
    });
  }
  return [...byKey.values()];
}

function weatherFromPro(observation: Record<string, unknown>): WeatherFields {
  const weather = emptyWeather();
  weather.temperatureC = num(observation.temperature);
  weather.feelsLikeC = num(observation.feels_like);
  weather.dewPointC = num(observation.dew_point);
  weather.humidityPct = num(observation.humidity);
  weather.precipitationRateMmH = num(observation.precipitation_rate);
  weather.precipitationAccumulatedMm = num(observation.precipitation_accumulated);
  weather.windSpeedMs = num(observation.wind_speed);
  weather.windGustMs = num(observation.wind_gust);
  weather.windDirectionDeg = num(observation.wind_direction);
  weather.uvIndex = num(observation.uv_index);
  weather.pressureHpa = num(observation.pressure);
  weather.solarIrradianceWm2 = num(observation.solar_irradiance);
  weather.icon = typeof observation.icon === "string" ? observation.icon : null;
  return weather;
}

function healthScore(health: unknown): number | null {
  if (!isRecord(health) || !isRecord(health.data_quality)) return null;
  return num(health.data_quality.score);
}

export function passesQod(score: number | null, minimum: number): boolean {
  if (minimum <= 0) return true;
  if (score === null) return false;
  return score >= minimum;
}

function segmentOf(value: unknown): TrailSegment | null {
  return value === "eastside" || value === "westside" ? value : null;
}

function num(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  return null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

async function getJson(
  fetchImpl: typeof fetch,
  url: string,
  init?: RequestInit,
): Promise<Record<string, unknown>> {
  const response = await fetchImpl(url, init);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} from ${url}`);
  }
  const payload: unknown = await response.json();
  if (!isRecord(payload)) {
    throw new Error(`Expected a JSON object from ${url}`);
  }
  return payload;
}
