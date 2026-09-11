import { describe, expect, it, vi } from "vitest";

import { RetrievalController } from "./retrieval.controller";
import { RetrievalService } from "./retrieval.service";

function createController() {
  const service = {
    search: vi.fn(),
    getContext: vi.fn(),
    getStatus: vi.fn(),
  } as unknown as RetrievalService;
  const controller = new RetrievalController(service);
  return { controller, service };
}

describe("RetrievalController", () => {
  it("search delegates to service", async () => {
    const { controller, service } = createController();
    (service.search as any).mockResolvedValue([{ title: "T" }]);

    const result = await controller.search({ query: "q" });
    expect(result).toEqual([{ title: "T" }]);
    expect(service.search).toHaveBeenCalledWith({ query: "q" });
  });

  it("getContext delegates to service", async () => {
    const { controller, service } = createController();
    (service.getContext as any).mockResolvedValue({ context: "ctx" });

    const result = await controller.getContext({
      question: "q",
      maxSources: 3,
    });
    expect(result).toEqual({ context: "ctx" });
    expect(service.getContext).toHaveBeenCalledWith("q", 3);
  });

  it("getStatus delegates to service", async () => {
    const { controller, service } = createController();
    (service.getStatus as any).mockResolvedValue({ ready: true });

    const result = await controller.getStatus();
    expect(result).toEqual({ ready: true });
    expect(service.getStatus).toHaveBeenCalled();
  });
});
