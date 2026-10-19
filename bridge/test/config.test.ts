import assert from "node:assert/strict";
import test from "node:test";

import { ConfigError, loadConfig } from "../src/config.js";
import { DRY_RUN_PREFIX } from "../src/streams.js";

const KEY = `0x${"ab".repeat(32)}`;

test("dry run is the default and does not require a key", () => {
  const config = loadConfig({ STREAMR_SAMPLE: "1" });
  assert.equal(config.dryRun, true);
  assert.equal(config.streamIdPrefix, DRY_RUN_PREFIX);
  assert.equal(config.privateKey, undefined);
  assert.equal(config.sample, true);
  assert.deepEqual(config.adapters, []);
});

test("live mode requires a key and a real prefix", () => {
  assert.throws(
    () => loadConfig({ STREAMR_DRY_RUN: "0", BELTLINE_API_URL: "http://api:8000" }),
    /STREAMR_PRIVATE_KEY/,
  );
  assert.throws(
    () =>
      loadConfig({
        STREAMR_DRY_RUN: "0",
        STREAMR_PRIVATE_KEY: KEY,
        STREAMR_STREAM_ID_PREFIX: DRY_RUN_PREFIX,
        BELTLINE_API_URL: "http://api:8000",
      }),
    /dry-run placeholder/,
  );
  const config = loadConfig({
    STREAMR_DRY_RUN: "0",
    STREAMR_PRIVATE_KEY: KEY,
    STREAMR_STREAM_ID_PREFIX: "0xABCDEF0000000000000000000000000000000001/open-depin-telemetry",
    BELTLINE_API_URL: "http://127.0.0.1:8000",
  });
  assert.equal(config.dryRun, false);
  assert.equal(config.streamIdPrefix, "0xabcdef0000000000000000000000000000000001/open-depin-telemetry");
  assert.equal(config.weatherSource, "local");
});

test("a rejected key is not echoed", () => {
  const secret = "not-a-key";
  try {
    loadConfig({ STREAMR_PRIVATE_KEY: secret, STREAMR_SAMPLE: "1" });
    assert.fail("expected ConfigError");
  } catch (error) {
    assert.ok(error instanceof ConfigError);
    assert.equal(error.message.includes(secret), false);
  }
});

test("pro source refuses to invent station ids", () => {
  assert.throws(
    () =>
      loadConfig({
        STREAMR_SAMPLE: "1",
        WEATHERXM_SOURCE: "pro",
        WEATHERXM_API_KEY: "test-key",
      }),
    /WEATHERXM_STATION_IDS/,
  );
});
