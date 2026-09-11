import { HttpException, HttpStatus } from "@nestjs/common";
import { HttpService } from "@nestjs/axios";
import { of, throwError } from "rxjs";
import { describe, expect, it, vi } from "vitest";

import { IngestionService } from "./ingestion.service";

function createService() {
  const httpService = {
    post: vi.fn(),
    get: vi.fn(),
  } as unknown as HttpService;
  const service = new IngestionService(httpService);
  return { service, httpService };
}

async function expectBadGateway(promise: Promise<unknown>) {
  const err = (await promise.catch((e) => e)) as HttpException;
  expect(err).toBeInstanceOf(HttpException);
  expect(err.getStatus()).toBe(HttpStatus.BAD_GATEWAY);
}

describe("IngestionService", () => {
  it("run posts to /ingest and returns data", async () => {
    const { service, httpService } = createService();
    (httpService.post as any).mockReturnValue(
      of({ data: { status: "started" } }),
    );

    const result = await service.run({ force: true, checkNew: true });
    expect(result).toEqual({ status: "started" });
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
});
