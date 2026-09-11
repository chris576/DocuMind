import { Readable } from "stream";
import { describe, expect, it, vi } from "vitest";
import type { Response } from "express";

import { GenerationController } from "./generation.controller";
import { GenerationService } from "./generation.service";

function createController() {
  const service = {
    ask: vi.fn(),
    askStream: vi.fn(),
    getStatus: vi.fn(),
    chatInit: vi.fn(),
    chatMessage: vi.fn(),
    chatMessageStream: vi.fn(),
  } as unknown as GenerationService;
  const controller = new GenerationController(service);
  return { controller, service };
}

describe("GenerationController", () => {
  it("ask delegates to service", async () => {
    const { controller, service } = createController();
    (service.ask as any).mockResolvedValue({ answer: "A" });

    const result = await controller.ask({ question: "Q" });
    expect(result).toEqual({ answer: "A" });
    expect(service.ask).toHaveBeenCalledWith({ question: "Q" });
  });

  it("askStream sets SSE headers and pipes the stream", async () => {
    const { controller, service } = createController();
    const stream = { pipe: vi.fn() } as unknown as Readable;
    (service.askStream as any).mockResolvedValue(stream);

    const setHeader = vi.fn();
    const res = { setHeader } as unknown as Response;

    await controller.askStream({ question: "Q" }, res);
    expect(setHeader).toHaveBeenCalledWith("Content-Type", "text/event-stream");
    expect(setHeader).toHaveBeenCalledWith("Cache-Control", "no-cache");
    expect(setHeader).toHaveBeenCalledWith("Connection", "keep-alive");
    expect(stream.pipe).toHaveBeenCalledWith(res);
  });

  it("getStatus delegates to service", async () => {
    const { controller, service } = createController();
    (service.getStatus as any).mockResolvedValue({ status: "ok" });

    const result = await controller.getStatus();
    expect(result).toEqual({ status: "ok" });
    expect(service.getStatus).toHaveBeenCalled();
  });

  it("chatInit delegates to service", async () => {
    const { controller, service } = createController();
    (service.chatInit as any).mockResolvedValue({ status: "initialized" });

    const result = await controller.chatInit({ documentId: 1 });
    expect(result).toEqual({ status: "initialized" });
    expect(service.chatInit).toHaveBeenCalledWith({ documentId: 1 });
  });

  it("chatMessage delegates to service", async () => {
    const { controller, service } = createController();
    (service.chatMessage as any).mockResolvedValue({ message: "hi back" });

    const result = await controller.chatMessage({ chatId: "c1", message: "hi" });
    expect(result).toEqual({ message: "hi back" });
    expect(service.chatMessage).toHaveBeenCalledWith({
      chatId: "c1",
      message: "hi",
    });
  });

  it("chatMessageStream sets SSE headers and pipes the stream", async () => {
    const { controller, service } = createController();
    const stream = { pipe: vi.fn() } as unknown as Readable;
    (service.chatMessageStream as any).mockResolvedValue(stream);

    const setHeader = vi.fn();
    const res = { setHeader } as unknown as Response;

    await controller.chatMessageStream({ chatId: "c1", message: "hi" }, res);
    expect(setHeader).toHaveBeenCalledWith("Content-Type", "text/event-stream");
    expect(stream.pipe).toHaveBeenCalledWith(res);
  });
});
