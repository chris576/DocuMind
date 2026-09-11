import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "../src/api/client";
import * as api from "../src/api";

vi.mock("../src/api/client", () => ({
  API_BASE: "",
  apiClient: { post: vi.fn(), get: vi.fn() },
}));

const mockedPost = vi.mocked(apiClient.post);
const mockedGet = vi.mocked(apiClient.get);

describe("api", () => {
  beforeEach(() => {
    mockedPost.mockReset();
    mockedGet.mockReset();
  });

  it("searchDocuments posts to /api/retrieval/search", async () => {
    mockedPost.mockResolvedValue({ data: [{ title: "T" }] });
    const result = await api.searchDocuments({ query: "q" });
    expect(result).toEqual([{ title: "T" }]);
    expect(mockedPost).toHaveBeenCalledWith("/api/retrieval/search", {
      query: "q",
    });
  });

  it("askQuestion posts to /api/generation/ask", async () => {
    mockedPost.mockResolvedValue({ data: { answer: "A" } });
    const result = await api.askQuestion({ question: "Q" });
    expect(result).toEqual({ answer: "A" });
    expect(mockedPost).toHaveBeenCalledWith("/api/generation/ask", {
      question: "Q",
    });
  });

  it("runIngestion posts to /api/ingestion/run", async () => {
    mockedPost.mockResolvedValue({ data: { status: "started" } });
    const result = await api.runIngestion({ force: true, checkNew: false });
    expect(result).toEqual({ status: "started" });
    expect(mockedPost).toHaveBeenCalledWith("/api/ingestion/run", {
      force: true,
      checkNew: false,
    });
  });

  it("runIngestionSync posts to /api/ingestion/run/sync", async () => {
    mockedPost.mockResolvedValue({ data: { status: "completed" } });
    const result = await api.runIngestionSync({ force: false });
    expect(result).toEqual({ status: "completed" });
    expect(mockedPost).toHaveBeenCalledWith("/api/ingestion/run/sync", {
      force: false,
    });
  });

  it("getIngestionStatus gets /api/ingestion/status", async () => {
    mockedGet.mockResolvedValue({ data: { initialized: true } });
    const result = await api.getIngestionStatus();
    expect(result).toEqual({ initialized: true });
    expect(mockedGet).toHaveBeenCalledWith("/api/ingestion/status");
  });

  it("getRetrievalStatus gets /api/retrieval/status", async () => {
    mockedGet.mockResolvedValue({ data: { ready: true } });
    const result = await api.getRetrievalStatus();
    expect(result).toEqual({ ready: true });
    expect(mockedGet).toHaveBeenCalledWith("/api/retrieval/status");
  });

  it("getGenerationStatus gets /api/generation/status", async () => {
    mockedGet.mockResolvedValue({ data: { status: "ok" } });
    const result = await api.getGenerationStatus();
    expect(result).toEqual({ status: "ok" });
    expect(mockedGet).toHaveBeenCalledWith("/api/generation/status");
  });
});
