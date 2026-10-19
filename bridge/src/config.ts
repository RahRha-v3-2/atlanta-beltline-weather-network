import { DRY_RUN_PREFIX, assertLivePrefix, normalizePrefix } from "./streams.js";

export type WeatherSource = "local" | "pro" | "both";
export type AdapterName = "weatherxm" | "geodnet" | "wingbits" | "helium" | "air-quality";
export type TrailSegment = "eastside" | "westside";

const ADAPTERS: readonly AdapterName[] = [
  "weatherxm",
  "geodnet",
  "wingbits",
  "helium",
  "air-quality",
];

export interface BridgeConfig {
  dryRun: boolean;
  privateKey?: string;
  streamIdPrefix: string;
  pollIntervalMs: number;
  once: boolean;
  allowPublicWeatherxm: boolean;
  sample: boolean;
  adapters: AdapterName[];
  weatherSource?: WeatherSource;
  beltlineApiUrl?: string;
  weatherXmApiKey?: string;
  weatherXmApiBaseUrl: string;
  stationIds: string[];
  segment?: TrailSegment;
  qodMinScore: number;
}

export interface CliFlags {
  dryRun?: boolean;
  once?: boolean;
  sample?: boolean;
}

export class ConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ConfigError";
  }
}

export function loadConfig(env: NodeJS.ProcessEnv, flags: CliFlags = {}): BridgeConfig {
  const dryRun = flags.dryRun ?? boolEnv(env.STREAMR_DRY_RUN, true);
  const sample = flags.sample ?? boolEnv(env.STREAMR_SAMPLE, false);
  const once = flags.once ?? boolEnv(env.STREAMR_ONCE, false);
  const privateKey = blankToUndefined(env.STREAMR_PRIVATE_KEY);
  const prefixInput = blankToUndefined(env.STREAMR_STREAM_ID_PREFIX);
  const streamIdPrefix = normalizePrefix(prefixInput ?? (dryRun ? DRY_RUN_PREFIX : ""));
  const pollIntervalMs = parsePositiveInt(env.STREAMR_POLL_INTERVAL_MS, 60_000);
  const allowPublicWeatherxm = boolEnv(env.STREAMR_ALLOW_PUBLIC_WEATHERXM, false);
  const qodMinScore = parseUnitInterval(env.QOD_MIN_SCORE, 0);
  const weatherXmApiKey = blankToUndefined(env.WEATHERXM_API_KEY);
  const weatherXmApiBaseUrl = (
    blankToUndefined(env.WEATHERXM_API_BASE_URL) ?? "https://pro.weatherxm.com/api/v1"
  ).replace(/\/+$/, "");
  const stationIds = splitList(env.WEATHERXM_STATION_IDS);
  const beltlineApiUrl = blankToUndefined(env.BELTLINE_API_URL)?.replace(/\/+$/, "");
  const segment = parseSegment(env.WEATHERXM_SEGMENT);
  const adapters = parseAdapters(env.STREAMR_ADAPTERS);
  const weatherSource = resolveWeatherSource(env.WEATHERXM_SOURCE, {
    beltlineApiUrl,
    weatherXmApiKey,
    stationIds,
  });

  if (pollIntervalMs < 1000) {
    throw new ConfigError("STREAMR_POLL_INTERVAL_MS must be at least 1000.");
  }
  if (privateKey && !/^0x[0-9a-fA-F]{64}$/.test(privateKey)) {
    throw new ConfigError("STREAMR_PRIVATE_KEY must be a 0x-prefixed 32-byte hex key. It was not printed.");
  }
  if (!dryRun) {
    if (!privateKey) {
      throw new ConfigError(
        "STREAMR_PRIVATE_KEY is required when STREAMR_DRY_RUN=0. A dry run needs no key and publishes nothing.",
      );
    }
    if (!prefixInput) {
      throw new ConfigError(
        "STREAMR_STREAM_ID_PREFIX is required when STREAMR_DRY_RUN=0. Example: /open-depin-telemetry",
      );
    }
    try {
      assertLivePrefix(streamIdPrefix);
    } catch (error) {
      throw new ConfigError(error instanceof Error ? error.message : String(error));
    }
  }
  if (sample && !dryRun) {
    throw new ConfigError("STREAMR_SAMPLE is only valid in a dry run. Sample messages are never published.");
  }

  const wantsWeather = adapters.includes("weatherxm");
  if (wantsWeather && !weatherSource && !sample) {
    throw new ConfigError(
      "No WeatherXM source is configured. Set BELTLINE_API_URL, or WEATHERXM_API_KEY plus WEATHERXM_STATION_IDS, or STREAMR_SAMPLE=1 for a dry run.",
    );
  }

  return {
    dryRun,
    privateKey,
    streamIdPrefix: streamIdPrefix || DRY_RUN_PREFIX,
    pollIntervalMs,
    once,
    allowPublicWeatherxm,
    sample,
    adapters: wantsWeather && !weatherSource && sample ? adapters.filter((name) => name !== "weatherxm") : adapters,
    weatherSource: wantsWeather ? weatherSource : undefined,
    beltlineApiUrl,
    weatherXmApiKey,
    weatherXmApiBaseUrl,
    stationIds,
    segment,
    qodMinScore,
  };
}

function resolveWeatherSource(
  raw: string | undefined,
  available: { beltlineApiUrl?: string; weatherXmApiKey?: string; stationIds: string[] },
): WeatherSource | undefined {
  const hasPro = Boolean(available.weatherXmApiKey && available.stationIds.length > 0);
  const hasLocal = Boolean(available.beltlineApiUrl);
  const requested = blankToUndefined(raw)?.toLowerCase();
  if (!requested || requested === "auto") {
    if (hasLocal && hasPro) return "both";
    if (hasPro) return "pro";
    if (hasLocal) return "local";
    return undefined;
  }
  if (requested !== "local" && requested !== "pro" && requested !== "both") {
    throw new ConfigError("WEATHERXM_SOURCE must be auto, local, pro, or both.");
  }
  if ((requested === "local" || requested === "both") && !hasLocal) {
    throw new ConfigError("WEATHERXM_SOURCE includes local, so BELTLINE_API_URL is required.");
  }
  if ((requested === "pro" || requested === "both") && !available.weatherXmApiKey) {
    throw new ConfigError("WEATHERXM_SOURCE includes pro, so WEATHERXM_API_KEY is required.");
  }
  if ((requested === "pro" || requested === "both") && available.stationIds.length === 0) {
    throw new ConfigError(
      "WEATHERXM_SOURCE includes pro, so WEATHERXM_STATION_IDS is required. The bridge does not search a map for stations.",
    );
  }
  return requested;
}

function parseAdapters(raw: string | undefined): AdapterName[] {
  const text = blankToUndefined(raw);
  if (!text) return ["weatherxm"];
  const names = splitList(text);
  if (names.length === 0) return ["weatherxm"];
  for (const name of names) {
    if (!ADAPTERS.includes(name as AdapterName)) {
      throw new ConfigError(
        `Unknown STREAMR_ADAPTERS entry ${JSON.stringify(name)}. Known: ${ADAPTERS.join(", ")}.`,
      );
    }
  }
  return names as AdapterName[];
}

function parseSegment(raw: string | undefined): TrailSegment | undefined {
  const text = blankToUndefined(raw)?.toLowerCase();
  if (!text) return undefined;
  if (text === "eastside" || text === "westside") return text;
  throw new ConfigError("WEATHERXM_SEGMENT must be eastside, westside, or unset.");
}

function parseUnitInterval(raw: string | undefined, fallback: number): number {
  const text = blankToUndefined(raw);
  if (!text) return fallback;
  const value = Number(text);
  if (!Number.isFinite(value) || value < 0 || value > 1) {
    throw new ConfigError("QOD_MIN_SCORE must be a number from 0 to 1.");
  }
  return value;
}

function parsePositiveInt(raw: string | undefined, fallback: number): number {
  const text = blankToUndefined(raw);
  if (!text) return fallback;
  const value = Number(text);
  if (!Number.isInteger(value) || value <= 0) {
    throw new ConfigError("STREAMR_POLL_INTERVAL_MS must be a positive integer.");
  }
  return value;
}

function boolEnv(raw: string | undefined, fallback: boolean): boolean {
  const text = blankToUndefined(raw)?.toLowerCase();
  if (!text) return fallback;
  if (["1", "true", "yes", "on"].includes(text)) return true;
  if (["0", "false", "no", "off"].includes(text)) return false;
  throw new ConfigError(`Expected a boolean environment value, got ${JSON.stringify(text)}.`);
}

function blankToUndefined(raw: string | undefined): string | undefined {
  const text = raw?.trim();
  return text ? text : undefined;
}

function splitList(raw: string | undefined): string[] {
  return (raw ?? "")
    .split(",")
    .map((part) => part.trim())
    .filter((part) => part.length > 0);
}
