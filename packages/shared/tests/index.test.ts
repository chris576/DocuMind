import { describe, expect, expectTypeOf, it } from "vitest";

import * as shared from "../src/index";
import type {
  AIStatus,
  AskRequestDto,
  AskResponseDto,
  ChatInitRequestDto,
  ChatInitResponseDto,
  ChatMessage,
  ChatMessageRequestDto,
  ChatMessageResponseDto,
  Document,
  IGenerationService,
  IIngestionService,
  ILLMProvider,
  IMessageQueue,
  IngestionRunDto,
  IngestionStatusDto,
  IRetrievalService,
  IVectorDB,
  RAGStatus,
  SearchRequestDto,
  SearchResult,
} from "../src/index";

describe("shared enums", () => {
  it("LLMProviderType maps all five providers", () => {
    expect(shared.LLMProviderType.OPENAI).toBe("openai");
    expect(shared.LLMProviderType.OLLAMA).toBe("ollama");
    expect(shared.LLMProviderType.AZURE).toBe("azure");
    expect(shared.LLMProviderType.CUSTOM).toBe("custom");
    expect(shared.LLMProviderType.ANTHROPIC).toBe("anthropic");
    expect(Object.values(shared.LLMProviderType).sort()).toEqual([
      "anthropic",
      "azure",
      "custom",
      "ollama",
      "openai",
    ]);
  });

  it("VectorDBType maps all three backends", () => {
    expect(shared.VectorDBType.CHROMA).toBe("chroma");
    expect(shared.VectorDBType.QDRANT).toBe("qdrant");
    expect(shared.VectorDBType.PGVECTOR).toBe("pgvector");
    expect(Object.values(shared.VectorDBType).sort()).toEqual([
      "chroma",
      "pgvector",
      "qdrant",
    ]);
  });

  it("ProcessingStatus enumerates lifecycle states", () => {
    expect(shared.ProcessingStatus.PENDING).toBe("pending");
    expect(shared.ProcessingStatus.PROCESSING).toBe("processing");
    expect(shared.ProcessingStatus.COMPLETE).toBe("complete");
    expect(shared.ProcessingStatus.FAILED).toBe("failed");
    expect(Object.values(shared.ProcessingStatus).sort()).toEqual([
      "complete",
      "failed",
      "pending",
      "processing",
    ]);
  });

  it("QueueName enumerates all queues", () => {
    expect(shared.QueueName.INGESTION).toBe("ingestion");
    expect(shared.QueueName.RETRIEVAL).toBe("retrieval");
    expect(shared.QueueName.GENERATION).toBe("generation");
    expect(shared.QueueName.STATUS).toBe("status");
    expect(Object.values(shared.QueueName).sort()).toEqual([
      "generation",
      "ingestion",
      "retrieval",
      "status",
    ]);
  });
});

describe("shared public API surface", () => {
  it("re-exports all four enums at runtime", () => {
    expect(shared).toHaveProperty("LLMProviderType");
    expect(shared).toHaveProperty("VectorDBType");
    expect(shared).toHaveProperty("ProcessingStatus");
    expect(shared).toHaveProperty("QueueName");
  });
});

describe("types (compile-time contract)", () => {
  it("Document carries the expected fields", () => {
    expectTypeOf<Document>().toMatchTypeOf<{
      id: number;
      title: string;
      content?: string;
      correspondent?: string;
      documentType?: string;
      tags?: string[];
      createdAt?: string;
      updatedAt?: string;
    }>();
  });

  it("SearchResult carries the expected fields", () => {
    expectTypeOf<SearchResult>().toMatchTypeOf<{
      title: string;
      correspondent: string;
      date: string;
      score: number;
      crossScore: number;
      snippet: string;
      docId?: number;
    }>();
  });

  it("ChatMessage restricts the role union", () => {
    expectTypeOf<ChatMessage>().toMatchTypeOf<{
      role: "user" | "assistant" | "system";
      content: string;
    }>();
  });

  it("RAGStatus carries the indexing block", () => {
    expectTypeOf<RAGStatus>().toMatchTypeOf<{
      serverUp: boolean;
      dataLoaded: boolean;
      indexReady: boolean;
      chromaReady: boolean;
      bm25Ready: boolean;
      indexingStatus: {
        running: boolean;
        lastIndexed?: string;
        documentsCount: number;
        upToDate: boolean;
        message: string;
      };
    }>();
  });

  it("AIStatus carries status and optional model", () => {
    expectTypeOf<AIStatus>().toMatchTypeOf<{
      status: string;
      model?: string;
    }>();
  });
});

describe("DTOs (compile-time contract)", () => {
  it("SearchRequestDto", () => {
    expectTypeOf<SearchRequestDto>().toMatchTypeOf<{
      query: string;
      fromDate?: string;
      toDate?: string;
      correspondent?: string;
      maxResults?: number;
    }>();
  });

  it("AskRequestDto", () => {
    expectTypeOf<AskRequestDto>().toMatchTypeOf<{
      question: string;
      maxTokens?: number;
      temperature?: number;
    }>();
  });

  it("AskResponseDto", () => {
    expectTypeOf<AskResponseDto>().toMatchTypeOf<{
      answer: string;
      sources: SearchResult[];
      metrics?: {
        promptTokens: number;
        completionTokens: number;
        totalTokens: number;
      };
      model?: string;
      provider?: string;
    }>();
  });

  it("IngestionRunDto", () => {
    expectTypeOf<IngestionRunDto>().toMatchTypeOf<{
      force?: boolean;
      checkNew?: boolean;
    }>();
  });

  it("IngestionStatusDto", () => {
    expectTypeOf<IngestionStatusDto>().toMatchTypeOf<{
      running: boolean;
      lastIndexed?: string;
      documentsCount: number;
      upToDate: boolean;
      message: string;
    }>();
  });

  it("ChatInitRequestDto", () => {
    expectTypeOf<ChatInitRequestDto>().toMatchTypeOf<{
      documentId?: number;
      documentTitle?: string;
      documentContent?: string;
    }>();
  });

  it("ChatInitResponseDto", () => {
    expectTypeOf<ChatInitResponseDto>().toMatchTypeOf<{
      chatId: string;
      status: string;
    }>();
  });

  it("ChatMessageRequestDto", () => {
    expectTypeOf<ChatMessageRequestDto>().toMatchTypeOf<{
      chatId: string;
      message: string;
    }>();
  });

  it("ChatMessageResponseDto", () => {
    expectTypeOf<ChatMessageResponseDto>().toMatchTypeOf<{
      chatId: string;
      message: string;
      role: string;
    }>();
  });
});

describe("service interfaces (compile-time contract)", () => {
  it("IVectorDB", () => {
    expectTypeOf<IVectorDB>().toMatchTypeOf<{
      initialize(): Promise<boolean>;
      addDocuments(
        documents: Array<{
          id: string;
          title: string;
          content: string;
          metadata?: Record<string, any>;
        }>,
      ): Promise<void>;
      search(query: string, topK?: number): Promise<SearchResult[]>;
      deleteCollection(): Promise<void>;
      getStatus(): Promise<{ ready: boolean; documentCount: number }>;
    }>();
  });

  it("ILLMProvider", () => {
    expectTypeOf<ILLMProvider>().toMatchTypeOf<{
      generateText(
        prompt: string,
        options?: { maxTokens?: number; temperature?: number },
      ): Promise<string>;
      generateStream(
        prompt: string,
        options?: { maxTokens?: number; temperature?: number },
      ): AsyncIterable<string>;
      checkStatus(): Promise<{ status: string; model?: string }>;
    }>();
  });

  it("IMessageQueue", () => {
    expectTypeOf<IMessageQueue>().toMatchTypeOf<{
      publish(queue: string, message: any): Promise<void>;
      consume(
        queue: string,
        handler: (message: any) => Promise<void>,
      ): Promise<void>;
      close(): Promise<void>;
    }>();
  });

  it("IRetrievalService", () => {
    expectTypeOf<IRetrievalService>().toMatchTypeOf<{
      search(
        query: string,
        options?: { fromDate?: string; toDate?: string; correspondent?: string },
      ): Promise<SearchResult[]>;
    }>();
  });

  it("IGenerationService", () => {
    expectTypeOf<IGenerationService>().toMatchTypeOf<{
      generateAnswer(
        question: string,
        context: string,
        options?: { maxSources?: number },
      ): Promise<{
        answer: string;
        sources: any[];
        metrics?: {
          promptTokens: number;
          completionTokens: number;
          totalTokens: number;
        };
      }>;
    }>();
  });

  it("IIngestionService", () => {
    expectTypeOf<IIngestionService>().toMatchTypeOf<{
      ingestDocuments(
        documents: Array<{
          id: number;
          title: string;
          content: string;
          metadata?: Record<string, any>;
        }>,
      ): Promise<void>;
      getStatus(): Promise<{
        running: boolean;
        lastIndexed?: string;
        documentsCount: number;
      }>;
    }>();
  });
});
