import assert from "node:assert/strict";
import test from "node:test";

import { loadConfig } from "../src/config.js";
import { pollWeatherXm } from "../src/adapters/weatherxm.js";

const PRO_BODY = {
  observation: {
    timestamp: "2026-10-18T15:00:00.000Z",
    temperature: 21.5,
    feels_like: 21,
    dew_point: 10,
    humidity: 55,
    precipitation_rate: 0.2,
    precipitation_accumulated: 3,
    wind_speed: 1.5,
    wind_gust: 2.5,
    wind_direction: 90,
    uv_index: 1,
    pressure: 1010,
    solar_irradiance: 100,
    icon: "clear-day",
  },
  health: { data_quality: { score: 0.91 } },
  location: { lat: 1, lon: 2, elevation: 3 },
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

test("pro readings stay on the fleet stream unless a segment is set", async () => {
  const seen: string[] = [];
  const fetchImpl: typeof fetch = async (input, init) => {
    const url = String(input);
    seen.push(url);
    assert.equal((init?.headers as Record<string, string>)["X-API-KEY"], "test-key");
    return jsonResponse(PRO_BODY);
  };
  const config = loadConfig({
    STREAMR_DRY_RUN: "1",
    WEATHERXM_SOURCE: "pro",
    WEATHERXM_API_KEY: "test-key",
    WEATHERXM_STATION_IDS: "fixture-station",
    WEATHERXM_API_BASE_URL: "https://pro.weatherxm.com/api/v1",
  });
  const messages = await pollWeatherXm(config, fetchImpl);
  assert.deepEqual(seen, ["https://pro.weatherxm.com/api/v1/stations/fixture-station/latest"]);
  assert.equal(messages.length, 1);
  assert.equal(messages[0]?.stream, "fleet/weatherxm");
  assert.equal(messages[0]?.weather?.temperatureC, 21.5);
  assert.equal(messages[0]?.weather?.windSpeedMs, 1.5);
  assert.equal(messages[0]?.license, "WeatherXM terms");
  assert.equal(messages[0]?.publishable, false);
  assert.equal(messages[0]?.segment, null);
});

test("an explicit host segment also targets beltline/weather", async () => {
  const fetchImpl: typeof fetch = async () => jsonResponse(PRO_BODY);
  const config = loadConfig({
    WEATHERXM_SOURCE: "pro",
    WEATHERXM_API_KEY: "test-key",
    WEATHERXM_STATION_IDS: "fixture-station",
    WEATHERXM_SEGMENT: "eastside",
    STREAMR_ALLOW_PUBLIC_WEATHERXM: "1",
  });
  const messages = await pollWeatherXm(config, fetchImpl);
  assert.deepEqual(
    messages.map((message) => message.stream),
    ["fleet/weatherxm", "beltline/weather"],
  );
  assert.equal(messages[0]?.publishable, true);
  assert.equal(messages[1]?.segment, "eastside");
});

test("local API tags beltline only for eastside or westside", async () => {
  const fetchImpl: typeof fetch = async () =>
    jsonResponse({
      observations: [
        {
          station_id: "host-1",
          observed_at: "2026-10-18T15:00:00.000Z",
          segment: "eastside",
          temperature_c: 30,
          source: "weatherxm",
          qod_score: 0.99,
        },
        {
          station_id: "other-1",
          observed_at: "2026-10-18T15:00:00.000Z",
          segment: null,
          temperature_c: 10,
          source: "weatherxm",
        },
      ],
    });
  const config = loadConfig({ BELTLINE_API_URL: "http://api:8000", WEATHERXM_SOURCE: "local" });
  const messages = await pollWeatherXm(config, fetchImpl);
  assert.deepEqual(
    messages.map((message) => [message.source.stationId, message.stream]),
    [
      ["host-1", "fleet/weatherxm"],
      ["host-1", "beltline/weather"],
      ["other-1", "fleet/weatherxm"],
    ],
  );
});

test("qod threshold drops a weak score and a missing score", async () => {
  let healthCalls = 0;
  const fetchImpl: typeof fetch = async (input) => {
    const url = String(input);
    if (url.endsWith("/health")) {
      healthCalls += 1;
      return jsonResponse({ health: { data_quality: { score: 0.2 } } });
    }
    return jsonResponse({
      observation: { timestamp: "2026-10-18T15:00:00.000Z", temperature: 1 },
      location: { lat: 1, lon: 2, elevation: 3 },
    });
  };
  const config = loadConfig({
    WEATHERXM_SOURCE: "pro",
    WEATHERXM_API_KEY: "test-key",
    WEATHERXM_STATION_IDS: "fixture-station",
    QOD_MIN_SCORE: "0.5",
  });
  const messages = await pollWeatherXm(config, fetchImpl);
  assert.equal(healthCalls, 1);
  assert.equal(messages.length, 0);
});
