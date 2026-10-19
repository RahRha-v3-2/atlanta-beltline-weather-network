import path from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

import { buildAdapters } from "./adapters/index.js";
import { ConfigError, loadConfig } from "./config.js";
import { DryRunPublisher, GatewayPublisher } from "./publisher.js";
import { runBridge } from "./run.js";

async function main(): Promise<number> {
  const { values } = parseArgs({
    options: {
      once: { type: "boolean", default: false },
      "dry-run": { type: "boolean", default: false },
      sample: { type: "boolean", default: false },
    },
  });
  const controller = new AbortController();
  process.on("SIGINT", () => controller.abort());
  process.on("SIGTERM", () => controller.abort());
  try {
    const config = loadConfig(process.env, {
      once: values.once ? true : undefined,
      dryRun: values["dry-run"] ? true : undefined,
      sample: values.sample ? true : undefined,
    });
    const adapters = buildAdapters(config);
    const publisher = config.dryRun
      ? new DryRunPublisher((line) => console.log(line))
      : new GatewayPublisher(await liveGateway(config.privateKey!));
    if (!config.dryRun) {
      console.error(
        "Live mode can create a missing stream on first publish. Creation is a Polygon transaction and needs POL for gas. No stream has been created by this process yet.",
      );
    }
    return await runBridge({
      config,
      adapters,
      publisher,
      log: (line) => console.error(line),
      signal: controller.signal,
    });
  } catch (error) {
    console.error(error instanceof ConfigError || error instanceof Error ? error.message : String(error));
    return error instanceof ConfigError ? 2 : 1;
  }
}

async function liveGateway(privateKey: string) {
  const { createStreamGateway } = await import("./streamr-gateway.js");
  return createStreamGateway(privateKey);
}

const entry = process.argv[1];
if (entry && path.resolve(entry) === fileURLToPath(import.meta.url)) {
  process.exitCode = await main();
}
