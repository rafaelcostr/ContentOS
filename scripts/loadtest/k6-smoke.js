/**
 * ContentOS gateway smoke load test (k6) — V5.5.4
 *
 * Usage:
 *   k6 run scripts/loadtest/k6-smoke.js
 *   BASE_URL=https://api.example.com k6 run scripts/loadtest/k6-smoke.js
 */

import http from "k6/http";
import { check, sleep } from "k6";

const BASE = __ENV.BASE_URL || "http://localhost:8000";
const AUTH_TOKEN = __ENV.AUTH_TOKEN || "";

export const options = {
  scenarios: {
    smoke: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "20s", target: 10 },
        { duration: "40s", target: 30 },
        { duration: "20s", target: 0 },
      ],
      gracefulRampDown: "10s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.02"],
    http_req_duration: ["p(95)<800"],
    checks: ["rate>0.95"],
  },
};

export default function () {
  const health = http.get(`${BASE}/health`);
  check(health, {
    "health 200": (r) => r.status === 200,
  });

  const metrics = http.get(`${BASE}/metrics`);
  check(metrics, {
    "metrics 200": (r) => r.status === 200 || r.status === 404,
  });

  if (AUTH_TOKEN) {
    const headers = { Authorization: `Bearer ${AUTH_TOKEN}` };
    const projects = http.get(`${BASE}/api/v1/projects`, { headers });
    check(projects, {
      "projects auth": (r) => r.status === 200 || r.status === 401,
    });
  }

  sleep(0.2);
}

export function handleSummary(data) {
  const p95 = data.metrics.http_req_duration?.values?.["p(95)"];
  const failed = data.metrics.http_req_failed?.values?.rate;
  return {
    stdout: [
      "ContentOS k6 smoke summary",
      `  p95 latency: ${p95 != null ? p95.toFixed(1) : "n/a"} ms`,
      `  fail rate: ${failed != null ? (failed * 100).toFixed(2) : "n/a"}%`,
    ].join("\n"),
  };
}
