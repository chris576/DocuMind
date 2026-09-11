import { HttpException, HttpStatus } from "@nestjs/common";
import { HttpService } from "@nestjs/axios";
import { of, throwError } from "rxjs";
import { describe, expect, it, vi } from "vitest";

import { RetrievalService } from "./retrieval.service";
import { PipelineRegistry } from "../pipelines/pipeline-registry";

function createService() {
  const httpService = {
    post: vi.fn(),
    get: vi.fn(),
  } as unknown as HttpService;
  const registry = new PipelineRegistry();
  const service = new RetrievalService(httpService, registry);
  return { service, httpService };
}

async function expectBadGateway(promise: Promise<unknown>) {
  const err = (await promise.catch((e) => e)) as HttpException;
  expect(err).toBeInstanceOf(HttpException);
  expect(err.getStatus()).toBe(HttpStatus.BAD_GATEWAY);
}

describe("RetrievalService", () => {
  it("search posts to /search and maps snake_case to camelCase", async () => {
    const { service, httpService } = createService();
    (httpService.post as any).mockReturnValue(
      of({
        data: [
          {
            title: "T",
            correspondent: "C",
            date: "2024-01-01",
            score: 1,
            cross_score: 2,
            snippet: "S",
            doc_id: 3,
          },
        ],
      }),
    );

    const results = await service.search({ query: "q" });
    expect(results[0]).toEqual({
      title: "T",
      correspondent: "C",
      date: "2024-01-01",
      score: 1,
      crossScore: 2,
      snippet: "S",
      docId: 3,
    });
  });

  it("search passes filter fields and defaults max_results to 20", async () => {
    const { service, httpService } = createService();
    (httpService.post as any).mockReturnValue(of({ data: [] }));

    await service.search({
      query: "q",
      fromDate: "2024-01-01",
      toDate: "2024-12-31",
      correspondent: "ACME",
    });
    expect(httpService.post).toHaveBeenCalledWith(
      "http://localhost:8002/search",
      {
        query: "q",
        from_date: "2024-01-01",
        to_date: "2024-12-31",
        correspondent: "ACME",
        max_results: 20,
      },
    );
  });

  it("search returns empty array when pipeline returns a non-array", async () => {
    const { service, httpService } = createService();
    (httpService.post as any).mockReturnValue(of({ data: { not: "array" } }));

    const results = await service.search({ query: "q" });
    expect(results).toEqual([]);
  });

  it("search throws 502 on error", async () => {
    const { service, httpService } = createService();
    (httpService.post as any).mockReturnValue(
      throwError(() => new Error("down")),
    );
    await expectBadGateway(service.search({ query: "q" }));
  });

  it("getContext posts to /context and returns data", async () => {
    const { service, httpService } = createService();
    (httpService.post as any).mockReturnValue(
      of({ data: { context: "ctx" } }),
    );

    const result = await service.getContext("question?", 3);
    expect(result).toEqual({ context: "ctx" });
    expect(httpService.post).toHaveBeenCalledWith(
      "http://localhost:8002/context",
      { question: "question?", max_sources: 3 },
    );
  });

  it("getContext defaults maxSources to 5", async () => {
    const { service, httpService } = createService();
    (httpService.post as any).mockReturnValue(of({ data: {} }));

    await service.getContext("question?");
    expect(httpService.post).toHaveBeenCalledWith(
      "http://localhost:8002/context",
      { question: "question?", max_sources: 5 },
    );
  });

  it("getContext throws 502 on error", async () => {
    const { service, httpService } = createService();
    (httpService.post as any).mockReturnValue(
      throwError(() => new Error("down")),
    );
    await expectBadGateway(service.getContext("q"));
  });

  it("getStatus gets /status and returns data", async () => {
    const { service, httpService } = createService();
    (httpService.get as any).mockReturnValue(
      of({ data: { service: "retrieval-pipeline" } }),
    );

    const result = await service.getStatus();
    expect(result).toEqual({ service: "retrieval-pipeline" });
    expect(httpService.get).toHaveBeenCalledWith(
      "http://localhost:8002/status",
    );
  });

  it("getStatus throws 502 on error", async () => {
    const { service, httpService } = createService();
    (httpService.get as any).mockReturnValue(
      throwError(() => new Error("down")),
    );
    await expectBadGateway(service.getStatus());
  });
});
