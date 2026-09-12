import { HttpException } from "@nestjs/common";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { AppConfigService } from "./app-config.service";

function tempConfigFile(): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "documind-config-"));
  return path.join(dir, "config.json");
}

describe("AppConfigService", () => {
  const originalConfigFile = process.env.CONFIG_FILE;
  const originalPaperlessUrl = process.env.PAPERLESS_API_URL;
  const originalPaperlessToken = process.env.PAPERLESS_API_TOKEN;
  const originalOpenAiKey = process.env.OPENAI_API_KEY;
  const originalOpencodePassword = process.env.OPENCODE_PASSWORD;

  beforeEach(() => {
    process.env.CONFIG_FILE = tempConfigFile();
    process.env.PAPERLESS_API_URL = "http://paperless:8000";
    process.env.PAPERLESS_API_TOKEN = "secret-token";
    process.env.OPENAI_API_KEY = "openai-key";
    process.env.OPENCODE_PASSWORD = "oc-pw";
  });

  afterEach(() => {
    restore(process.env, "CONFIG_FILE", originalConfigFile);
    restore(process.env, "PAPERLESS_API_URL", originalPaperlessUrl);
    restore(process.env, "PAPERLESS_API_TOKEN", originalPaperlessToken);
    restore(process.env, "OPENAI_API_KEY", originalOpenAiKey);
    restore(process.env, "OPENCODE_PASSWORD", originalOpencodePassword);
  });

  it("returns defaults when no file exists", () => {
    const service = new AppConfigService();
    const config = service.getConfig();
    expect(config.version).toBe(1);
    expect(config.llm.provider).toBe("ollama");
    expect(config.vectorDb.collection).toBe("documents");
  });

  it("resolves the dms slice from env fallback", () => {
    const service = new AppConfigService();
    const slice = service.getSlice("dms");
    expect(slice).toMatchObject({
      document_provider: "paperless",
      document_provider_url: "http://paperless:8000",
      document_provider_token: "secret-token",
    });
  });

  it("resolves the llm slice with env-referenced api key", () => {
    const service = new AppConfigService();
    service.saveConfig({
      llm: { provider: "openai", model: "gpt-4", apiKeyEnv: "OPENAI_API_KEY" },
    });
    const slice = service.getSlice("llm");
    expect(slice).toMatchObject({
      provider: "openai",
      model: "gpt-4",
      api_key: "openai-key",
    });
  });

  it("resolves the llm slice for opencode", () => {
    const service = new AppConfigService();
    service.saveConfig({
      llm: {
        provider: "opencode",
        opencodeBaseUrl: "http://opencode:4096",
        opencodeUsername: "oc",
        opencodePasswordEnv: "OPENCODE_PASSWORD",
        opencodeModel: "opencode/gpt-5",
      },
    });
    const slice = service.getSlice("llm");
    expect(slice).toMatchObject({
      provider: "opencode",
      opencode_base_url: "http://opencode:4096",
      opencode_username: "oc",
      opencode_password: "oc-pw",
      opencode_model: "opencode/gpt-5",
    });
  });

  it("resolves the connectors slice from configured connectors", () => {
    const service = new AppConfigService();
    service.saveConfig({
      connectors: [
        { id: "paperless", type: "paperless", enabled: true, url: "http://p:8000" },
        { id: "obsidian", type: "docspell", enabled: true, collection: "obs_vault" },
      ],
    });
    const slice = service.getSlice("connectors") as Array<Record<string, unknown>>;
    expect(slice).toHaveLength(2);
    expect(slice[0]).toMatchObject({ id: "paperless", collection: "paperless" });
    expect(slice[1]).toMatchObject({ id: "obsidian", collection: "obs_vault" });
  });

  it("returns an env-fallback connector when none configured", () => {
    const service = new AppConfigService();
    const slice = service.getSlice("connectors") as Array<Record<string, unknown>>;
    expect(slice).toHaveLength(1);
    expect(slice[0]).toMatchObject({
      id: "paperless",
      type: "paperless",
      url: "http://paperless:8000",
      token: "secret-token",
    });
  });

  it("lists collections via getCollections", () => {
    const service = new AppConfigService();
    service.saveConfig({
      connectors: [
        { id: "paperless", type: "paperless", enabled: true },
        { id: "obsidian", type: "docspell", enabled: true, collection: "obs_vault" },
      ],
    });
    expect(service.getCollections()).toEqual(["paperless", "obs_vault"]);
  });

  it("returns the collections slice", () => {
    const service = new AppConfigService();
    service.saveConfig({
      connectors: [{ id: "paperless", type: "paperless", enabled: true }],
    });
    expect(service.getSlice("collections")).toEqual(["paperless"]);
  });

  it("returns 404 for an unknown slice", () => {
    const service = new AppConfigService();
    expect(() => service.getSlice("nope")).toThrow(HttpException);
  });

  it("redacts URL credentials on getConfig", () => {
    const service = new AppConfigService();
    service.saveConfig({
      vectorDb: { pgvectorUrl: "postgresql://user:pass@host:5432/db" },
    });
    const config = service.getConfig();
    expect(config.vectorDb.pgvectorUrl).toBe(
      "postgresql://user:***@host:5432/db",
    );
  });

  it("preserves an existing URL secret when saving a masked value", () => {
    const service = new AppConfigService();
    service.saveConfig({
      vectorDb: { pgvectorUrl: "postgresql://user:realpass@host:5432/db" },
    });
    service.saveConfig({
      vectorDb: { pgvectorUrl: "postgresql://user:***@host:5432/db" },
    });
    const slice = service.getSlice("vector-db") as Record<string, unknown>;
    expect(slice.pgvector_url).toBe("postgresql://user:realpass@host:5432/db");
  });
});

function restore(env: NodeJS.ProcessEnv, key: string, value: string | undefined) {
  if (value === undefined) {
    delete env[key];
  } else {
    env[key] = value;
  }
}
