import { describe, expect, it, beforeEach, afterEach } from "vitest";

import { validateEnv } from "../src/index";

let savedJwt: string | undefined;
let savedUrl: string | undefined;
let savedToken: string | undefined;

function setValid() {
  process.env.JWT_SECRET = "a".repeat(32);
  process.env.PAPERLESS_API_URL = "http://paperless:8000";
  process.env.PAPERLESS_API_TOKEN = "tok";
}

beforeEach(() => {
  savedJwt = process.env.JWT_SECRET;
  savedUrl = process.env.PAPERLESS_API_URL;
  savedToken = process.env.PAPERLESS_API_TOKEN;
  delete process.env.JWT_SECRET;
  delete process.env.PAPERLESS_API_URL;
  delete process.env.PAPERLESS_API_TOKEN;
});

afterEach(() => {
  process.env.JWT_SECRET = savedJwt;
  process.env.PAPERLESS_API_URL = savedUrl;
  process.env.PAPERLESS_API_TOKEN = savedToken;
});

describe("validateEnv", () => {
  it("returns parsed env with defaults for a valid environment", () => {
    setValid();
    const env = validateEnv();
    expect(env.JWT_SECRET).toBe("a".repeat(32));
    // Vitest setzt NODE_ENV=test; das Schema erlaubt diesen Wert.
    expect(env.NODE_ENV).toBe("test");
    expect(env.DOCUMENT_PROVIDER).toBe("paperless");
    expect(env.VECTOR_DB_TYPE).toBe("chroma");
    expect(env.BACKEND_PORT).toBe("3001");
  });

  it("throws for a missing required JWT_SECRET", () => {
    delete process.env.JWT_SECRET;
    expect(() => validateEnv()).toThrow("Invalid environment configuration");
  });

  it("throws for an invalid url", () => {
    process.env.JWT_SECRET = "a".repeat(32);
    process.env.PAPERLESS_API_URL = "not-a-url";
    process.env.PAPERLESS_API_TOKEN = "tok";
    expect(() => validateEnv()).toThrow("Invalid environment configuration");
  });

  it("applies OLLAMA_API_URL default", () => {
    setValid();
    const env = validateEnv();
    expect(env.OLLAMA_API_URL).toBe("http://localhost:11434");
  });
});
