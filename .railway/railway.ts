import { defineRailway, github, preserve, project, redis, service } from "railway/iac";
import type { VariableValue } from "railway/iac";

// Railway Infrastructure as Code for the dogwalker project.
// Replaces the deprecated per-service railway.json files (Config as Code stops
// being read on 2026-12-01). Preview with `railway config plan`; a human runs
// `railway config apply` after reading the plan.

const REPO = "BryanOwens012/dogwalker";
const PYTHON_BUILD = "pip install -r requirements.txt";

// Every service reads the same secrets. Values are set in the Railway dashboard,
// never in this file: `preserve()` keeps whatever Railway already holds, and a
// variable omitted here would be planned for deletion.
const SECRET_NAMES = [
  "ANTHROPIC_API_KEY",
  "GITHUB_REPO",
  "GITHUB_TOKEN",
  "SLACK_BOT_TOKEN",
  "SLACK_APP_TOKEN",
  "DOGS",
] as const;

const createPreservedSecrets = (): Record<(typeof SECRET_NAMES)[number], VariableValue> =>
  Object.fromEntries(SECRET_NAMES.map((name) => [name, preserve()])) as Record<
    (typeof SECRET_NAMES)[number],
    VariableValue
  >;

interface PythonServiceOptions {
  rootDirectory: string;
  start: string;
  build?: string;
  redisUrl: VariableValue;
}

// One Python process per service, built with Nixpacks from a subdirectory of this
// repo. No HTTP healthcheck: neither the Slack Socket Mode bot nor the Celery
// processes listen on PORT, so Railway's HTTP healthcheck could never return 200.
const createPythonService = (
  name: string,
  { rootDirectory, start, build = PYTHON_BUILD, redisUrl }: PythonServiceOptions,
) =>
  service(name, {
    source: github(REPO, { branch: "main", rootDirectory }),
    build: { builder: "NIXPACKS", buildCommand: build },
    start,
    deploy: { restartPolicyType: "ON_FAILURE", restartPolicyMaxRetries: 10 },
    env: { ...createPreservedSecrets(), REDIS_URL: redisUrl },
  });

export default defineRailway(() => {
  const cache = redis("redis");
  const redisUrl = cache.env.REDIS_URL;

  const orchestrator = createPythonService("orchestrator", {
    rootDirectory: "apps/orchestrator",
    start: "python src/bot.py",
    redisUrl,
  });

  const worker = createPythonService("worker", {
    rootDirectory: "apps/worker",
    // Playwright's pip package ships no browser; the screenshot tools need Chromium.
    build: `${PYTHON_BUILD} && playwright install chromium`,
    start: "celery -A src.celery_app worker --loglevel=info",
    redisUrl,
  });

  const beat = createPythonService("beat", {
    rootDirectory: "apps/worker",
    start: "celery -A src.celery_app beat --loglevel=info",
    redisUrl,
  });

  return project("dogwalker", {
    resources: [cache, orchestrator, worker, beat],
  });
});
