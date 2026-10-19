import assert from "node:assert/strict";
import test from "node:test";

import { loadConfig } from "../src/config.js";
import type { StreamGateway } from "../src/gateway.js";
import { GatewayPublisher } from "../src/publisher.js";
import { runCycle } from "../src/run.js";
import { sampleMessage } from "../src/sample.js";
import type { TelemetryMessage } from "../src/schema.js";

function gateway(): StreamGateway & { ids: string[]; published: unknown[] } {
  const ids: string[] = [];
  const published: unknown[] = [];
  return {
    ids,
    published,
    async getOrCreateStream(props) {
      ids.push(props.id);
      return {
        id: props.id,
        async publish(content) {
          published.push(content);
          return { streamId: props.id };
        },
      };
    },
    async grantPublicSubscribe() {
      throw new Error("grant should not run during publish");
    },
    async destroy() {
      return undefined;
    },
  };
}

function reading(publishable: boolean): TelemetryMessage {
  return {
    ...sampleMessage(),
    sample: false,
    publishable,
    publishBlockReason: publishable ? null : "blocked in test",
    source: {
      network: "weatherxm",
      stationId: "fixture-station",
      adapter: "weatherxm",
      adapterStatus: "implemented",
    },
    license: "WeatherXM terms",
  };
}

test("live publish uses getOrCreateStream and does not send blocked messages", async () => {
  const config = loadConfig({
    STREAMR_DRY_RUN: "0",
    STREAMR_PRIVATE_KEY: `0x${"11".repeat(32)}`,
    STREAMR_STREAM_ID_PREFIX: "/open-depin-telemetry",
    STREAMR_ALLOW_PUBLIC_WEATHERXM: "1",
    BELTLINE_API_URL: "http://api:8000",
  });
  const client = gateway();
  const publisher = new GatewayPublisher(client);
  const result = await runCycle(
    { ...config, dryRun: false, allowPublicWeatherxm: true },
    [
      {
        id: "weatherxm",
        stream: "fleet/weatherxm",
        status: "implemented",
        note: "",
        poll: async () => [reading(true), reading(false)],
      },
    ],
    publisher,
  );
  assert.equal(result.published, 1);
  assert.equal(result.skipped, 1);
  assert.deepEqual(client.ids, ["/open-depin-telemetry/fleet/weatherxm"]);
  assert.equal(client.published.length, 1);
});

test("a dry run does not call Streamr", async () => {
  const config = loadConfig({ STREAMR_SAMPLE: "1" });
  const client = gateway();
  let lines = "";
  const result = await runCycle(
    config,
    [
      {
        id: "sample",
        stream: "fleet/weatherxm",
        status: "sample",
        note: "",
        poll: async () => [sampleMessage()],
      },
    ],
    {
      async publish(streamId, message) {
        lines += JSON.stringify({ streamId, message });
      },
    },
  );
  assert.equal(client.ids.length, 0);
  assert.equal(result.published, 0);
  assert.equal(result.logged, 1);
  assert.match(lines, /sample-not-a-station/);
  assert.match(lines, /dry-run\/open-depin-telemetry\/fleet\/weatherxm/);
});
