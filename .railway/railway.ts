import { defineRailway, github, preserve, project, redis, service } from "railway/iac";

// Railway Infrastructure as Code for the dogwalker project.
// Replaces the deprecated per-service railway.json files (Config as Code stops
// being read on 2026-12-01). Preview with `railway config plan`; apply with
// `railway config apply` (Bryan runs apply, never an agent).

const REPO = "BryanOwens012/dogwalker";
const PYTHON_BUILD = "pip install -r requirements.txt";

// Every service reads the same secrets. Values are set in the Railway dashboard,
// never in this file: `preserve()` keeps whatever Railway already holds, and a
// variable omitted here would be planned for deletion.
const secrets = {
  ANTHROPIC_API_KEY: preserve(),
  GITHUB_REPO: preserve(),
  GITHUB_TOKEN: preserve(),
  SLACK_BOT_TOKEN: preserve(),
  SLACK_APP_TOKEN: preserve(),
  DOGS: preserve(),
};

// Carried over from railway.json. No HTTP healthcheck is configured: neither the
// Slack Socket Mode bot nor the Celery processes listen on PORT, so Railway's
// HTTP healthcheck could never return 200.
const restartOnFailure = {
  restartPolicyType: "ON_FAILURE",
  restartPolicyMaxRetries: 10,
} as const;

export default defineRailway(() => {
  const cache = redis("redis");

  const orchestrator = service("orchestrator", {
    source: github(REPO, { branch: "main", rootDirectory: "apps/orchestrator" }),
    build: { builder: "NIXPACKS", buildCommand: PYTHON_BUILD },
    start: "python src/bot.py",
    deploy: restartOnFailure,
    env: { ...secrets, REDIS_URL: cache.env.REDIS_URL },
  });

  const worker = service("worker", {
    source: github(REPO, { branch: "main", rootDirectory: "apps/worker" }),
    // Playwright's pip package ships no browser; the screenshot tools need Chromium.
    build: { builder: "NIXPACKS", buildCommand: `${PYTHON_BUILD} && playwright install chromium` },
    start: "celery -A src.celery_app worker --loglevel=info",
    deploy: restartOnFailure,
    env: { ...secrets, REDIS_URL: cache.env.REDIS_URL },
  });

  const beat = service("beat", {
    source: github(REPO, { branch: "main", rootDirectory: "apps/worker" }),
    build: { builder: "NIXPACKS", buildCommand: PYTHON_BUILD },
    start: "celery -A src.celery_app beat --loglevel=info",
    deploy: restartOnFailure,
    env: { ...secrets, REDIS_URL: cache.env.REDIS_URL },
  });

  return project("dogwalker", {
    resources: [cache, orchestrator, worker, beat],
  });
});
