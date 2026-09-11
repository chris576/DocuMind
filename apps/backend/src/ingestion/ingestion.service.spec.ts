import { HttpException, HttpStatus } from "@nestjs/common";
import { HttpService } from "@nestjs/axios";
import { of, throwError } from "rxjs";
import { describe, expect, it, vi } from "vitest";

import { IngestionService } from "./ingestion.service";
import { IngestionJobStore } from "./job-store";
import { PipelineRegistry } from "../pipelines/pipeline-registry";

function createService() {
  const httpService = {
    post: vi.fn(),
    get: vi.fn(),
  } as unknown as HttpService;
  const registry = new PipelineRegistry();
  const jobStore = new IngestionJobStore();
  const service = new IngestionService(httpService, registry, jobStore);
  return { service, httpService, jobStore };
}

async function expectBadGateway(promise: Promise<unknown>) {
  const err = (await promise.catch((e) => e)) as HttpException;
  expect(err).toBeInstanceOf(HttpException);
  expect(err.getStatus()).toBe(HttpStatus.BAD_GATEWAY);
}

describe("IngestionService", () => {
  it("run posts to /ingest and returns a running job", async () => {
    const { service, httpService } = createService();
    (httpService.post as any).mockReturnValue(
      of({ data: { status: "started", message: "started" } }),
    );

    const result = await service.run({ force: true, checkNew: true });
    expect(result.id).toBeTruthy();
    expect(result.namespace).toBe("paperless");
    expect(result.status).toBe("running");
    expect(httpService.post).toHaveBeenCalledWith(
      "http://localhost:8001/ingest",
      { force: true, check_new: true },
    );
  });

  it("run defaults force/checkNew to false", async () => {
    const { service, httpService } = createService();
    (httpService.post as any).mockReturnValue(of({ data: {} }));

    await service.run({});
    expect(httpService.post).toHaveBeenCalledWith(
      "http://localhost:8001/ingest",
      { force: false, check_new: false },
    );
  });

  it("run throws 502 on pipeline error", async () => {
    const { service, httpService } = createService();
    (httpService.post as any).mockReturnValue(
      throwError(() => new Error("down")),
    );
    await expectBadGateway(service.run({}));
  });

  it("runSync posts to /ingest/sync and returns data", async () => {
    const { service, httpService } = createService();
    (httpService.post as any).mockReturnValue(of({ data: { ok: true } }));

    const result = await service.runSync({ force: false });
    expect(result).toEqual({ ok: true });
    expect(httpService.post).toHaveBeenCalledWith(
      "http://localhost:8001/ingest/sync",
      { force: false, check_new: false },
    );
  });

  it("runSync throws 502 on error", async () => {
    const { service, httpService } = createService();
    (httpService.post as any).mockReturnValue(
      throwError(() => new Error("down")),
    );
    await expectBadGateway(service.runSync({}));
  });

  it("getStatus gets /status and returns data", async () => {
    const { service, httpService } = createService();
    (httpService.get as any).mockReturnValue(
      of({ data: { service: "ingestion-pipeline" } }),
    );

    const result = await service.getStatus();
    expect(result).toEqual({ service: "ingestion-pipeline" });
    expect(httpService.get).toHaveBeenCalledWith(
      "http://localhost:8001/status",
    );
  });

  it("getStatus throws 502 on error", async () => {
    const { service, httpService } = createService();
    (httpService.get as any).mockReturnValue(
      throwError(() => new Error("down")),
    );
    await expectBadGateway(service.getStatus());
  });

  it("getJob throws 404 for an unknown id", async () => {
    const { service } = createService();
    const err = (await service.getJob("nope").catch((e) => e)) as HttpException;
    expect(err).toBeInstanceOf(HttpException);
    expect(err.getStatus()).toBe(HttpStatus.NOT_FOUND);
  });
});
