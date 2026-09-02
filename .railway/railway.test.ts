import { createRailwayContext, project } from "railway/iac";
import type { ProjectDefinition, ServiceNode } from "railway/iac";
import { describe, expect, it } from "vitest";
import defineDogwalker from "./railway.ts";

// Evaluates railway.ts the way the Railway CLI does and checks the resulting
// graph, since `railway config plan` needs a linked project and cannot run in CI.

const REPO = "BryanOwens012/dogwalker";
const SECRET_NAMES = [
  "ANTHROPIC_API_KEY",
  "GITHUB_REPO",
  "GITHUB_TOKEN",
  "SLACK_BOT_TOKEN",
  "SLACK_APP_TOKEN",
  "DOGS",
];

const evaluateProject = async (): Promise<ProjectDefinition> => {
  const ctx = createRailwayContext({ command: "plan", environment: "production" });
  return defineDogwalker(ctx, project);
};

const findService = (definition: ProjectDefinition, name: string): ServiceNode => {
  const node = definition.resources?.flat().find((resource) => resource.address === `service.${name}`);
  if (!node || node.type !== "service") {
    throw new Error(`service.${name} missing from graph`);
  }
  return node;
};

describe("dogwalker Railway IaC", () => {
  it("declares the Redis database and the three Python services, nothing else", async () => {
    const definition = await evaluateProject();
    expect(definition.name).toBe("dogwalker");
    const addresses = definition.resources?.flat().map((resource) => resource.address);
    expect(addresses).toEqual(["database.redis", "service.orchestrator", "service.worker", "service.beat"]);
  });

  it.each([
    ["orchestrator", "apps/orchestrator", "python src/bot.py"],
    ["worker", "apps/worker", "celery -A src.celery_app worker --loglevel=info"],
    ["beat", "apps/worker", "celery -A src.celery_app beat --loglevel=info"],
  ])("%s builds from %s with Nixpacks and restarts on failure", async (name, rootDirectory, start) => {
    const node = findService(await evaluateProject(), name);
    expect(node.source).toEqual({ type: "github", repo: REPO, branch: "main", rootDirectory });
    expect(node.build?.builder).toBe("NIXPACKS");
    expect(node.build?.buildCommand).toContain("pip install -r requirements.txt");
    expect(node.deploy?.startCommand).toBe(start);
    expect(node.deploy?.restartPolicyType).toBe("ON_FAILURE");
    expect(node.deploy?.restartPolicyMaxRetries).toBe(10);
  });

  it("configures no HTTP healthcheck, since no service listens on PORT", async () => {
    const definition = await evaluateProject();
    for (const name of ["orchestrator", "worker", "beat"]) {
      const node = findService(definition, name);
      expect(node.deploy?.healthcheckPath).toBeUndefined();
      expect(node.deploy?.healthcheckTimeout).toBeUndefined();
    }
  });

  it("installs Chromium only for the worker", async () => {
    const definition = await evaluateProject();
    expect(findService(definition, "worker").build?.buildCommand).toContain("playwright install chromium");
    expect(findService(definition, "orchestrator").build?.buildCommand).not.toContain("playwright");
    expect(findService(definition, "beat").build?.buildCommand).not.toContain("playwright");
  });

  it("wires REDIS_URL to the Redis service and preserves every secret on every service", async () => {
    const definition = await evaluateProject();
    for (const name of ["orchestrator", "worker", "beat"]) {
      const variables = findService(definition, name).variables ?? {};
      expect(Object.keys(variables).sort()).toEqual([...SECRET_NAMES, "REDIS_URL"].sort());
      expect(variables.REDIS_URL).toEqual({ type: "reference", resource: "database.redis", output: "REDIS_URL" });
      for (const secret of SECRET_NAMES) {
        expect(variables[secret]).toEqual({ type: "preserve" });
      }
    }
  });
});
