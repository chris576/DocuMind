import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { PipelineRegistry } from "./pipeline-registry";

describe("PipelineRegistry", () => {
  const originalEnv = { ...process.env };

  beforeEach(() => {
    process.env.INGESTION_PIPELINE_URL = "http://ing:8001";
    process.env.RETRIEVAL_PIPELINE_URL = "http://ret:8002";
    process.env.GENERATION_PIPELINE_URL = "http://gen:8003";
    process.env.COLLECTION_NAME = "documents";
    delete process.env.PIPELINE_REGISTRY_JSON;
  });

  afterEach(() => {
    process.env = { ...originalEnv };
  });

  it("resolves the default namespace from env", () => {
    const registry = new PipelineRegistry();
    const pipeline = registry.resolve();
    expect(pipeline.namespace).toBe("paperless");
    expect(pipeline.ingestionUrl).toBe("http://ing:8001");
    expect(pipeline.collection).toBe("documents");
  });

  it("resolves namespaces from PIPELINE_REGISTRY_JSON", () => {
    process.env.PIPELINE_REGISTRY_JSON = JSON.stringify([
      { namespace: "obsidian", ingestionUrl: "http://obs:8001" },
    ]);
    const registry = new PipelineRegistry();
    const pipeline = registry.resolve("obsidian");
    expect(pipeline.collection).toBe("obsidian");
    expect(pipeline.ingestionUrl).toBe("http://obs:8001");
    expect(pipeline.retrievalUrl).toBe("http://ret:8002");
  });

  it("throws for an unknown namespace", () => {
    const registry = new PipelineRegistry();
    expect(() => registry.resolve("nope")).toThrow(/Unknown namespace/);
  });

  it("lists namespaces", () => {
    process.env.PIPELINE_REGISTRY_JSON = JSON.stringify([
      { namespace: "paperless" },
      { namespace: "obsidian" },
    ]);
    const registry = new PipelineRegistry();
    expect(registry.listNamespaces()).toEqual(["paperless", "obsidian"]);
  });
});
