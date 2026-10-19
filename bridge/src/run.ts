import { collect } from "./adapters/index.js";
import type { SourceAdapter } from "./adapters/types.js";
import type { BridgeConfig } from "./config.js";
import type { Publisher } from "./publisher.js";
import { streamId } from "./streams.js";

export interface CycleResult {
  messages: number;
  logged: number;
  published: number;
  skipped: number;
  notes: string[];
  errors: string[];
}

export async function runCycle(
  config: BridgeConfig,
  adapters: SourceAdapter[],
  publisher: Publisher,
  log: (line: string) => void = () => undefined,
): Promise<CycleResult> {
  const collected = await collect(adapters);
  for (const note of collected.notes) log(note);
  let logged = 0;
  let published = 0;
  let skipped = 0;
  for (const message of collected.messages) {
    const id = streamId(config.streamIdPrefix, message.stream);
    if (!message.publishable) {
      skipped += 1;
      if (config.dryRun) {
        await publisher.publish(id, message);
        logged += 1;
      } else {
        log(`skip ${id}: ${message.publishBlockReason ?? "not publishable"}`);
      }
      continue;
    }
    if (config.dryRun) {
      await publisher.publish(id, message);
      logged += 1;
      continue;
    }
    await publisher.publish(id, message);
    published += 1;
  }
  return {
    messages: collected.messages.length,
    logged,
    published,
    skipped,
    notes: collected.notes,
    errors: collected.errors,
  };
}

export async function runBridge(options: {
  config: BridgeConfig;
  adapters: SourceAdapter[];
  publisher: Publisher;
  log?: (line: string) => void;
  signal?: AbortSignal;
  sleep?: (ms: number, signal: AbortSignal) => Promise<void>;
}): Promise<number> {
  const log = options.log ?? ((line) => console.error(line));
  const sleep = options.sleep ?? delay;
  let exitCode = 0;
  do {
    const result = await runCycle(options.config, options.adapters, options.publisher, log);
    if (result.errors.length > 0) {
      exitCode = 1;
      for (const error of result.errors) log(error);
    }
    log(
      `cycle messages=${result.messages} logged=${result.logged} published=${result.published} skipped=${result.skipped} dryRun=${options.config.dryRun}`,
    );
    if (options.config.once || options.signal?.aborted) break;
    await sleep(options.config.pollIntervalMs, options.signal ?? new AbortController().signal);
  } while (!options.signal?.aborted);
  return exitCode;
}

function delay(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, ms);
    signal.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        resolve();
      },
      { once: true },
    );
  });
}
