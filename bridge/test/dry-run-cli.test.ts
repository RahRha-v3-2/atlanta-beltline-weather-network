import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";

test("the CLI dry run logs a sample and publishes nothing", async () => {
  const child = spawn(process.execPath, ["--import", "tsx", "src/cli.ts", "--once", "--sample"], {
    cwd: fileURLToPath(new URL("..", import.meta.url)),
    env: {
      PATH: process.env.PATH,
      STREAMR_DRY_RUN: "1",
    },
  });
  let stdout = "";
  let stderr = "";
  child.stdout.setEncoding("utf8");
  child.stderr.setEncoding("utf8");
  child.stdout.on("data", (chunk) => {
    stdout += chunk;
  });
  child.stderr.on("data", (chunk) => {
    stderr += chunk;
  });
  const code = await new Promise<number>((resolve, reject) => {
    child.on("error", reject);
    child.on("close", (status) => resolve(status ?? 1));
  });
  assert.equal(code, 0);
  assert.match(stdout, /"published":false/);
  assert.match(stdout, /sample-not-a-station/);
  assert.match(stdout, /dry-run\/open-depin-telemetry\/fleet\/weatherxm/);
  assert.match(stderr, /published=0/);
  assert.doesNotMatch(stdout + stderr, /0x[0-9a-fA-F]{64}/);
});
