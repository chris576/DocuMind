import { describe, expect, it, vi } from "vitest";

import { env, validateEnv } from "../src/index";

function setValid() {
  vi.stubEnv("PAPERLESS_API_URL", "http://paperless:8000");
  vi.stubEnv("PAPERLESS_API_TOKEN", "tok");
}

describe("env (module-level export)", () => {
  it("is parsed from the setup environment", () => {
    expect(env.PAPERLESS_API_URL).toBe("http://paperless:8000");
    expect(env.PAPERLESS_API_TOKEN).toBe("tok");
    expect(env.NODE_ENV).toBe("test");
  });
});

describe("validateEnv", () => {
  it("returns parsed env with defaults for a valid environment", () => {
    setValid();
    const parsed = validateEnv();
    expect(parsed.PAPERLESS_API_URL).toBe("http://paperless:8000");
    expect(parsed.PAPERLESS_API_TOKEN).toBe("tok");
    // Vitest setzt NODE_ENV=test; das Schema erlaubt diesen Wert.
    expect(parsed.NODE_ENV).toBe("test");
    expect(parsed.DOCUMENT_PROVIDER).toBe("paperless");
    expect(parsed.VECTOR_DB_TYPE).toBe("pgvector");
    expect(parsed.BACKEND_PORT).toBe("3001");
    expect(parsed.FRONTEND_PORT).toBe("3000");
    expect(parsed.OLLAMA_API_URL).toBe("http://localhost:11434");
    expect(parsed.OLLAMA_MODEL).toBe("llama3.2");
    expect(parsed.OPENCODE_BASE_URL).toBe("http://127.0.0.1:4096");
    expect(parsed.OPENCODE_USERNAME).toBe("opencode");
    expect(parsed.OPENCODE_PASSWORD).toBeUndefined();
    expect(parsed.OPENCODE_MODEL).toBeUndefined();
    expect(parsed.EXTERNAL_API_ENABLED).toBe("false");
    expect(parsed.EXTERNAL_API_MAX_TOKENS_PER_USER).toBe("5");
    expect(parsed.EXTERNAL_API_DEFAULT_MONTHLY_LIMIT).toBe("1000");
    expect(parsed.EXTERNAL_API_RATE_LIMIT_RPM).toBe("100");
    expect(parsed.INGESTION_PIPELINE_URL).toBe("http://localhost:8001");
    expect(parsed.RETRIEVAL_PIPELINE_URL).toBe("http://localhost:8002");
    expect(parsed.GENERATION_PIPELINE_URL).toBe("http://localhost:8003");
    expect(parsed.INGESTION_PORT).toBe("8001");
    expect(parsed.RETRIEVAL_PORT).toBe("8002");
    expect(parsed.GENERATION_PORT).toBe("8003");
    expect(parsed.INGESTION_HOST_PORT).toBe("8001");
    expect(parsed.RETRIEVAL_HOST_PORT).toBe("8002");
    expect(parsed.GENERATION_HOST_PORT).toBe("8003");
  });

  it("throws when PAPERLESS_API_URL is missing", () => {
    vi.stubEnv("PAPERLESS_API_URL", undefined);
    vi.stubEnv("PAPERLESS_API_TOKEN", "tok");
    expect(() => validateEnv()).toThrow("Invalid environment configuration");
  });

  it("throws when PAPERLESS_API_TOKEN is missing", () => {
    vi.stubEnv("PAPERLESS_API_URL", "http://paperless:8000");
    vi.stubEnv("PAPERLESS_API_TOKEN", undefined);
    expect(() => validateEnv()).toThrow("Invalid environment configuration");
  });

  it("throws for an invalid PAPERLESS_API_URL", () => {
    vi.stubEnv("PAPERLESS_API_URL", "not-a-url");
    vi.stubEnv("PAPERLESS_API_TOKEN", "tok");
    expect(() => validateEnv()).toThrow("Invalid environment configuration");
  });

  it("throws for an invalid DOCUMENT_PROVIDER", () => {
    setValid();
    vi.stubEnv("DOCUMENT_PROVIDER", "bogus");
    expect(() => validateEnv()).toThrow("Invalid environment configuration");
  });

  it("throws for an invalid VECTOR_DB_TYPE", () => {
    setValid();
    vi.stubEnv("VECTOR_DB_TYPE", "bogus");
    expect(() => validateEnv()).toThrow("Invalid environment configuration");
  });

  it("throws for an invalid NODE_ENV", () => {
    setValid();
    vi.stubEnv("NODE_ENV", "bogus");
    expect(() => validateEnv()).toThrow("Invalid environment configuration");
  });

  it("parses DOCUMENT_PROVIDER_URL and DOCUMENT_PROVIDER_TOKEN when set", () => {
    setValid();
    vi.stubEnv("DOCUMENT_PROVIDER", "docspell");
    vi.stubEnv("DOCUMENT_PROVIDER_URL", "http://docspell:7880");
    vi.stubEnv("DOCUMENT_PROVIDER_TOKEN", "ds-tok");
    const parsed = validateEnv();
    expect(parsed.DOCUMENT_PROVIDER).toBe("docspell");
    expect(parsed.DOCUMENT_PROVIDER_URL).toBe("http://docspell:7880");
    expect(parsed.DOCUMENT_PROVIDER_TOKEN).toBe("ds-tok");
  });

  it("parses LLM provider settings when provided", () => {
    setValid();
    vi.stubEnv("OPENAI_API_KEY", "sk-test");
    vi.stubEnv("ANTHROPIC_API_KEY", "ant-test");
    vi.stubEnv("CUSTOM_BASE_URL", "http://custom:9000");
    vi.stubEnv("CUSTOM_API_KEY", "custom-key");
    vi.stubEnv("CUSTOM_MODEL", "custom-model");
    vi.stubEnv("OPENCODE_BASE_URL", "http://opencode:4096");
    vi.stubEnv("OPENCODE_USERNAME", "oc");
    vi.stubEnv("OPENCODE_PASSWORD", "pw");
    vi.stubEnv("OPENCODE_MODEL", "opencode/gpt-5");
    const parsed = validateEnv();
    expect(parsed.OPENAI_API_KEY).toBe("sk-test");
    expect(parsed.ANTHROPIC_API_KEY).toBe("ant-test");
    expect(parsed.CUSTOM_BASE_URL).toBe("http://custom:9000");
    expect(parsed.CUSTOM_API_KEY).toBe("custom-key");
    expect(parsed.CUSTOM_MODEL).toBe("custom-model");
    expect(parsed.OPENCODE_BASE_URL).toBe("http://opencode:4096");
    expect(parsed.OPENCODE_USERNAME).toBe("oc");
    expect(parsed.OPENCODE_PASSWORD).toBe("pw");
    expect(parsed.OPENCODE_MODEL).toBe("opencode/gpt-5");
  });

  it("parses vector db settings when provided", () => {
    setValid();
    vi.stubEnv("VECTOR_DB_TYPE", "pgvector");
    vi.stubEnv("PGVECTOR_URL", "postgres://localhost:5432/documind");
    const parsed = validateEnv();
    expect(parsed.VECTOR_DB_TYPE).toBe("pgvector");
    expect(parsed.PGVECTOR_URL).toBe("postgres://localhost:5432/documind");
  });

  it("parses EXTERNAL_API settings when provided", () => {
    setValid();
    vi.stubEnv("EXTERNAL_API_ENABLED", "true");
    vi.stubEnv("EXTERNAL_API_MAX_TOKENS_PER_USER", "42");
    vi.stubEnv("EXTERNAL_API_DEFAULT_MONTHLY_LIMIT", "5000");
    vi.stubEnv("EXTERNAL_API_RATE_LIMIT_RPM", "60");
    const parsed = validateEnv();
    expect(parsed.EXTERNAL_API_ENABLED).toBe("true");
    expect(parsed.EXTERNAL_API_MAX_TOKENS_PER_USER).toBe("42");
    expect(parsed.EXTERNAL_API_DEFAULT_MONTHLY_LIMIT).toBe("5000");
    expect(parsed.EXTERNAL_API_RATE_LIMIT_RPM).toBe("60");
  });
});
