import { SCHEMA_ID, emptyWeather } from "./schema.js";
import type { TelemetryMessage } from "./schema.js";

export const SAMPLE_STATION_ID = "sample-not-a-station";

/** A labeled fake used only so a dry run has a payload to print. Never published. */
export function sampleMessage(now: Date = new Date()): TelemetryMessage {
  return {
    schema: SCHEMA_ID,
    observedAt: "2026-01-01T00:00:00.000Z",
    ingestedAt: now.toISOString(),
    source: {
      network: "weatherxm",
      stationId: SAMPLE_STATION_ID,
      adapter: "sample",
      adapterStatus: "sample",
    },
    stream: "fleet/weatherxm",
    segment: null,
    location: null,
    weather: emptyWeather(),
    health: null,
    airQuality: null,
    license: "not-data",
    publishable: false,
    publishBlockReason:
      "Sample payload for a dry run. Not a real station, not a BeltLine site, and never published.",
    sample: true,
  };
}
