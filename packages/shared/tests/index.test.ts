import { describe, expect, it } from "vitest";

import {
  LLMProviderType,
  ProcessingStatus,
  QueueName,
  Scope,
  VectorDBType,
} from "../src/index";

describe("shared enums", () => {
  it("LLMProviderType maps providers", () => {
    expect(LLMProviderType.OPENAI).toBe("openai");
    expect(LLMProviderType.OLLAMA).toBe("ollama");
    expect(LLMProviderType.ANTHROPIC).toBe("anthropic");
    expect(LLMProviderType.CUSTOM).toBe("custom");
    expect(Object.values(LLMProviderType)).toContain("azure");
  });

  it("VectorDBType maps vector backends", () => {
    expect(VectorDBType.CHROMA).toBe("chroma");
    expect(VectorDBType.QDRANT).toBe("qdrant");
    expect(VectorDBType.PGVECTOR).toBe("pgvector");
    expect(Object.values(VectorDBType)).toHaveLength(3);
  });

  it("Scope enumerates permission scopes", () => {
    expect(Scope.RAG_READ).toBe("rag:read");
    expect(Scope.CHAT_READ).toBe("chat:read");
    expect(Scope.METRICS_READ).toBe("metrics:read");
    expect(Scope.ADMIN).toBe("admin");
    expect(Object.values(Scope)).toHaveLength(4);
  });

  it("ProcessingStatus enumerates lifecycle states", () => {
    expect(ProcessingStatus.PENDING).toBe("pending");
    expect(ProcessingStatus.PROCESSING).toBe("processing");
    expect(ProcessingStatus.COMPLETE).toBe("complete");
    expect(ProcessingStatus.FAILED).toBe("failed");
  });

  it("QueueName enumerates queues", () => {
    expect(QueueName.INGESTION).toBe("ingestion");
    expect(QueueName.RETRIEVAL).toBe("retrieval");
    expect(QueueName.GENERATION).toBe("generation");
    expect(QueueName.STATUS).toBe("status");
  });
});

describe("shared types re-export", () => {
  it("exposes the public API surface", async () => {
    const mod = await import("../src/index");
    expect(mod).toHaveProperty("LLMProviderType");
    expect(mod).toHaveProperty("VectorDBType");
    expect(mod).toHaveProperty("Scope");
  });
});
