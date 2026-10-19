import assert from "node:assert/strict";
import test from "node:test";

import { createStreams } from "../src/create-streams.js";
import type { StreamGateway } from "../src/gateway.js";
import { STREAM_PATHS } from "../src/streams.js";

test("dry run lists every proposed stream and submits nothing", async () => {
  const lines: string[] = [];
  const result = await createStreams({
    prefix: "dry-run/open-depin-telemetry",
    dryRun: true,
    log: (line) => lines.push(line),
  });
  assert.equal(result.created, false);
  assert.equal(result.streamIds.length, STREAM_PATHS.length);
  assert.deepEqual(
    result.streamIds.map((id) => id.split("/").slice(-2).join("/")),
    [...STREAM_PATHS],
  );
  const parsed = lines.map((line) => JSON.parse(line) as { permission: { permissions: string[] }; onChain: boolean });
  assert.equal(parsed.length, 6);
  assert.deepEqual(parsed[0]?.permission.permissions, ["subscribe"]);
  assert.equal(parsed.every((row) => row.onChain === false), true);
  assert.match(lines.join("\n"), /POL/);
  assert.match(lines.join("\n"), /fleet\/geodnet-status/);
});

test("a live create grants public subscribe and not public publish", async () => {
  const created: string[] = [];
  const granted: string[] = [];
  const gateway: StreamGateway = {
    async getOrCreateStream(props) {
      created.push(props.id);
      return { id: props.id, async publish() { return undefined; } };
    },
    async grantPublicSubscribe(streamId) {
      granted.push(streamId);
    },
    async destroy() {
      return undefined;
    },
  };
  const result = await createStreams({
    prefix: "/open-depin-telemetry",
    dryRun: false,
    gateway,
    log: () => undefined,
  });
  assert.equal(result.created, true);
  assert.deepEqual(created, result.streamIds);
  assert.deepEqual(granted, result.streamIds);
  assert.equal(created.some((id) => id.endsWith("fleet/geodnet-status")), true);
});
