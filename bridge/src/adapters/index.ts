import type { BridgeConfig } from "../config.js";
import { sampleMessage } from "../sample.js";
import type { TelemetryMessage } from "../schema.js";
import { stubById } from "./stubs.js";
import type { SourceAdapter } from "./types.js";
import { createWeatherXmAdapter } from "./weatherxm.js";

export function buildAdapters(config: BridgeConfig, fetchImpl: typeof fetch = fetch): SourceAdapter[] {
  const adapters: SourceAdapter[] = [];
  for (const name of config.adapters) {
    if (name === "weatherxm") {
      if (config.weatherSource) adapters.push(createWeatherXmAdapter(config, fetchImpl));
      continue;
    }
    const stub = stubById(name);
    if (stub) adapters.push(stub);
  }
  if (config.sample) {
    adapters.push({
      id: "sample",
      stream: "fleet/weatherxm",
      status: "sample",
      note: "In-process sample payload. Not a station.",
      poll: async () => [sampleMessage()],
    });
  }
  return adapters;
}

export async function collect(adapters: SourceAdapter[]): Promise<{
  messages: TelemetryMessage[];
  notes: string[];
  errors: string[];
}> {
  const messages: TelemetryMessage[] = [];
  const notes: string[] = [];
  const errors: string[] = [];
  for (const adapter of adapters) {
    if (adapter.status === "stub") {
      notes.push(`${adapter.id}: ${adapter.note}`);
    }
    try {
      messages.push(...(await adapter.poll()));
    } catch (error) {
      errors.push(`${adapter.id}: ${error instanceof Error ? error.message : String(error)}`);
    }
  }
  return { messages, notes, errors };
}
