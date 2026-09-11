import { HttpException, HttpStatus } from "@nestjs/common";
import { HttpService } from "@nestjs/axios";
import { of, throwError } from "rxjs";
import { Readable } from "stream";
import { describe, expect, it, vi } from "vitest";

import { GenerationService } from "./generation.service";
import { PipelineRegistry } from "../pipelines/pipeline-registry";

function createService() {
  const httpService = {
    post: vi.fn(),
    get: vi.fn(),
  } as unknown as HttpService;
  const registry = new PipelineRegistry();
  const service = new GenerationService(httpService, registry);
  return { service, httpService };
}

async function expectBadGateway(promise: Promise<unknown>) {
  const err = (await promise.catch((e) => e)) as HttpException;
  expect(err).toBeInstanceOf(HttpException);
  expect(err.getStatus()).toBe(HttpStatus.BAD_GATEWAY);
}

describe("GenerationService", () => {
  it("ask posts to /generate and maps token metrics", async () => {
    const { service, httpService } = createService();
    (httpService.post as any).mockReturnValue(
      of({
        data: {
          answer: "A",
          prompt_tokens: 10,
          completion_tokens: 5,
          total_tokens: 15,
          model: "m",
          provider: "openai",
        },
      }),
    );

    const result = await service.ask({ question: "Q" });
    expect(result).toEqual({
      answer: "A",
      sources: [],
      metrics: {
        promptTokens: 10,
        completionTokens: 5,
        totalTokens: 15,
      },
      model: "m",
      provider: "openai",
    });
    expect(httpService.post).toHaveBeenCalledWith(
      "http://localhost:8003/generate",
      { question: "Q", max_tokens: undefined, temperature: undefined },
    );
  });

  it("ask throws 502 on error", async () => {
    const { service, httpService } = createService();
    (httpService.post as any).mockReturnValue(
      throwError(() => new Error("down")),
    );
    await expectBadGateway(service.ask({ question: "Q" }));
  });

  it("askStream posts with responseType stream and returns a Readable", async () => {
    const { service, httpService } = createService();
    const stream = new Readable({ read() {} });
    (httpService.post as any).mockReturnValue(of({ data: stream }));

    const result = await service.askStream({ question: "Q" });
    expect(result).toBe(stream);
    expect(httpService.post).toHaveBeenCalledWith(
      "http://localhost:8003/generate/stream",
      { question: "Q", max_tokens: undefined, temperature: undefined },
      { responseType: "stream" },
    );
  });

  it("askStream throws 502 on error", async () => {
    const { service, httpService } = createService();
    (httpService.post as any).mockReturnValue(
      throwError(() => new Error("down")),
    );
    await expectBadGateway(service.askStream({ question: "Q" }));
  });

  it("getStatus gets /status and returns data", async () => {
    const { service, httpService } = createService();
    (httpService.get as any).mockReturnValue(of({ data: { status: "ok" } }));

    const result = await service.getStatus();
    expect(result).toEqual({ status: "ok" });
    expect(httpService.get).toHaveBeenCalledWith(
      "http://localhost:8003/status",
    );
  });

  it("chatInit posts to /chat/init and returns data", async () => {
    const { service, httpService } = createService();
    (httpService.post as any).mockReturnValue(
      of({ data: { status: "initialized" } }),
    );

    const result = await service.chatInit({ documentId: 1 });
    expect(result).toEqual({ status: "initialized" });
    expect(httpService.post).toHaveBeenCalledWith(
      "http://localhost:8003/chat/init",
      { document_id: 1, document_title: undefined, document_content: undefined },
    );
  });

  it("chatInit throws 502 on error", async () => {
    const { service, httpService } = createService();
    (httpService.post as any).mockReturnValue(
      throwError(() => new Error("down")),
    );
    await expectBadGateway(service.chatInit({ documentId: 1 }));
  });

  it("chatMessage posts to /chat/message and returns data", async () => {
    const { service, httpService } = createService();
    (httpService.post as any).mockReturnValue(
      of({ data: { message: "hi back" } }),
    );

    const result = await service.chatMessage({ chatId: "c1", message: "hi" });
    expect(result).toEqual({ message: "hi back" });
    expect(httpService.post).toHaveBeenCalledWith(
      "http://localhost:8003/chat/message",
      { chat_id: "c1", message: "hi" },
    );
  });

  it("chatMessage throws 502 on error", async () => {
    const { service, httpService } = createService();
    (httpService.post as any).mockReturnValue(
      throwError(() => new Error("down")),
    );
    await expectBadGateway(
      service.chatMessage({ chatId: "c1", message: "hi" }),
    );
  });

  it("chatMessageStream posts with responseType stream", async () => {
    const { service, httpService } = createService();
    const stream = new Readable({ read() {} });
    (httpService.post as any).mockReturnValue(of({ data: stream }));

    const result = await service.chatMessageStream({
      chatId: "c1",
      message: "hi",
    });
    expect(result).toBe(stream);
    expect(httpService.post).toHaveBeenCalledWith(
      "http://localhost:8003/chat/message/stream",
      { chat_id: "c1", message: "hi" },
      { responseType: "stream" },
    );
  });

  it("chatMessageStream throws 502 on error", async () => {
    const { service, httpService } = createService();
    (httpService.post as any).mockReturnValue(
      throwError(() => new Error("down")),
    );
    await expectBadGateway(
      service.chatMessageStream({ chatId: "c1", message: "hi" }),
    );
  });
});
