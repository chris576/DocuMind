import { describe, expect, it, vi } from "vitest";

import { IngestionController } from "./ingestion.controller";
import { IngestionService } from "./ingestion.service";

function createController() {
  const service = {
    run: vi.fn(),
    runSync: vi.fn(),
    getStatus: vi.fn(),
    getJob: vi.fn(),
    listJobs: vi.fn(),
  } as unknown as IngestionService;
  const controller = new IngestionController(service);
  return { controller, service };
}

describe("IngestionController", () => {
  it("run delegates to service", async () => {
    const { controller, service } = createController();
    (service.run as any).mockResolvedValue({ status: "started" });

    const result = await controller.run({ force: true, checkNew: true });
    expect(result).toEqual({ status: "started" });
    expect(service.run).toHaveBeenCalledWith({ force: true, checkNew: true });
  });

  it("runSync delegates to service", async () => {
    const { controller, service } = createController();
    (service.runSync as any).mockResolvedValue({ ok: true });

    const result = await controller.runSync({ force: false });
    expect(result).toEqual({ ok: true });
    expect(service.runSync).toHaveBeenCalledWith({ force: false });
  });

  it("getStatus delegates to service", async () => {
    const { controller, service } = createController();
    (service.getStatus as any).mockResolvedValue({ initialized: true });

    const result = await controller.getStatus();
    expect(result).toEqual({ initialized: true });
    expect(service.getStatus).toHaveBeenCalled();
  });

  it("getJob delegates to service", async () => {
    const { controller, service } = createController();
    (service.getJob as any).mockResolvedValue({ id: "j1", status: "running" });

    const result = await controller.getJob("j1");
    expect(result).toEqual({ id: "j1", status: "running" });
    expect(service.getJob).toHaveBeenCalledWith("j1");
  });

  it("listJobs delegates to service", async () => {
    const { controller, service } = createController();
    (service.listJobs as any).mockResolvedValue([]);

    const result = await controller.listJobs();
    expect(result).toEqual([]);
    expect(service.listJobs).toHaveBeenCalled();
  });
});
