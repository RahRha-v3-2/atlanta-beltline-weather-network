import path from "node:path";
import { fileURLToPath } from "node:url";

import { ConfigError, loadConfig } from "./config.js";
import type { StreamGateway } from "./gateway.js";
import { proposedStreamIds } from "./streams.js";

export interface CreateStreamsResult {
  streamIds: string[];
  created: boolean;
}

/**
 * Dry-run prints the stream ids and the public-subscribe grant it would submit.
 * A live run calls getOrCreateStream and grantPermissions. Both of those can
 * send a Polygon transaction and need POL for gas. Nothing here is claimed
 * to exist already.
 */
export async function createStreams(options: {
  prefix: string;
  dryRun: boolean;
  gateway?: StreamGateway;
  log?: (line: string) => void;
}): Promise<CreateStreamsResult> {
  const log = options.log ?? ((line) => console.log(line));
  const streamIds = proposedStreamIds(options.prefix);
  if (options.dryRun) {
    for (const streamId of streamIds) {
      log(
        JSON.stringify({
          event: "create-streams-dry-run",
          streamId,
          permission: { public: true, permissions: ["subscribe"] },
          onChain: false,
          note: "Stream creation and a public subscribe grant are Polygon transactions and need POL for gas. This dry run did not submit them. This id is not a stream that exists.",
        }),
      );
    }
    return { streamIds, created: false };
  }
  if (!options.gateway) {
    throw new Error("A Streamr gateway is required when creating streams for real.");
  }
  log(
    "About to create or reuse streams and grant public subscribe. Those steps are on-chain on Polygon and need POL for gas. Public publish is not granted.",
  );
  for (const streamId of streamIds) {
    await options.gateway.getOrCreateStream({ id: streamId });
    await options.gateway.grantPublicSubscribe(streamId);
    log(JSON.stringify({ event: "create-streams", streamId, created: true }));
  }
  return { streamIds, created: true };
}

async function main(): Promise<number> {
  const dryFlag = process.argv.includes("--dry-run");
  try {
    const config = loadConfig(process.env, { dryRun: dryFlag ? true : undefined });
    if (!config.dryRun && !config.privateKey) {
      throw new ConfigError("STREAMR_PRIVATE_KEY is required to create streams.");
    }
    const gateway = config.dryRun ? undefined : await liveGateway(config.privateKey!);
    try {
      await createStreams({
        prefix: config.streamIdPrefix,
        dryRun: config.dryRun,
        gateway,
      });
    } finally {
      await gateway?.destroy();
    }
    return 0;
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    return 2;
  }
}

async function liveGateway(privateKey: string): Promise<StreamGateway> {
  const { createStreamGateway } = await import("./streamr-gateway.js");
  return createStreamGateway(privateKey);
}

const entry = process.argv[1];
if (entry && path.resolve(entry) === fileURLToPath(import.meta.url)) {
  process.exitCode = await main();
}
