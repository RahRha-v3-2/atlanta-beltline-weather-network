import assert from "node:assert/strict";
import test from "node:test";

import { buildAdapters } from "../src/adapters/index.js";
import { STUBS } from "../src/adapters/stubs.js";
import { loadConfig } from "../src/config.js";

test("non-WeatherXM adapters are stubs and emit nothing", async () => {
  assert.deepEqual(
    STUBS.map((adapter) => adapter.id),
    ["geodnet", "wingbits", "helium", "air-quality"],
  );
  for (const adapter of STUBS) {
    assert.equal(adapter.status, "stub");
    assert.deepEqual(await adapter.poll(), []);
  }
  const geodnet = STUBS.find((adapter) => adapter.id === "geodnet");
  assert.match(geodnet?.note ?? "", /No RTK correction data/);
  const config = loadConfig({
    STREAMR_SAMPLE: "1",
    STREAMR_ADAPTERS: "geodnet,wingbits,helium,air-quality",
  });
  const adapters = buildAdapters(config);
  const messages = (await Promise.all(adapters.map((adapter) => adapter.poll()))).flat();
  assert.equal(messages.length, 1);
  assert.equal(messages[0]?.sample, true);
});
