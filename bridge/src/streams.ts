/** Proposed stream paths. These are names, not streams that exist on Streamr. */

export const STREAM_PATHS = [
  "beltline/weather",
  "beltline/air-quality",
  "fleet/weatherxm",
  "fleet/geodnet-status",
  "fleet/wingbits",
  "fleet/helium",
] as const;

export type StreamPath = (typeof STREAM_PATHS)[number];

export const DRY_RUN_PREFIX = "dry-run/open-depin-telemetry";

const LIVE_PREFIX = /^(?:0x[0-9a-f]{40}\/.+|\/[a-z0-9][a-z0-9._/-]*)$/;

export function normalizePrefix(prefix: string): string {
  const trimmed = prefix.trim().replace(/\/+$/, "");
  if (trimmed.startsWith("0x") || trimmed.startsWith("0X")) {
    const slash = trimmed.indexOf("/");
    if (slash === -1) {
      return trimmed.toLowerCase();
    }
    return trimmed.slice(0, slash).toLowerCase() + trimmed.slice(slash);
  }
  return trimmed;
}

export function assertLivePrefix(prefix: string): void {
  if (prefix === DRY_RUN_PREFIX || prefix.startsWith("dry-run/")) {
    throw new Error(
      "STREAMR_STREAM_ID_PREFIX is still the dry-run placeholder. Set it to /your-path or 0x<your-address>/your-path before a live run.",
    );
  }
  if (!LIVE_PREFIX.test(prefix)) {
    throw new Error(
      "STREAMR_STREAM_ID_PREFIX must look like /open-depin-telemetry or 0x<40 hex chars>/open-depin-telemetry. This prototype does not invent an existing stream id.",
    );
  }
}

export function streamId(prefix: string, path: StreamPath): string {
  return `${normalizePrefix(prefix)}/${path}`;
}

export function proposedStreamIds(prefix: string): string[] {
  return STREAM_PATHS.map((path) => streamId(prefix, path));
}
