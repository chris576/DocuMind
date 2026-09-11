import { HttpException, HttpStatus } from "@nestjs/common";
import { afterEach, describe, expect, it } from "vitest";
import { PipelineRegistry } from "./pipeline-registry";
import { RestartService } from "./restart.service";

type RunCommand = (command: string, args: string[]) => Promise<unknown>;

function makeService(
  map: string | undefined,
  runCommand: RunCommand = async () => undefined,
): RestartService {
  if (map === undefined) {
    delete process.env.PIPELINE_CONTAINER_MAP;
  } else {
    process.env.PIPELINE_CONTAINER_MAP = map;
  }
  return new RestartService(new PipelineRegistry(), runCommand);
}

describe("RestartService", () => {
  const original = process.env.PIPELINE_CONTAINER_MAP;

  afterEach(() => {
    if (original === undefined) {
      delete process.env.PIPELINE_CONTAINER_MAP;
    } else {
      process.env.PIPELINE_CONTAINER_MAP = original;
    }
  });

  it("throws 501 when no container is mapped", async () => {
    const service = makeService(undefined);
    const err = (await service.restart("paperless").catch((e) => e)) as HttpException;
    expect(err.getStatus()).toBe(HttpStatus.NOT_IMPLEMENTED);
  });

  it("runs docker restart for a mapped namespace", async () => {
    const calls: string[][] = [];
    const service = makeService(
      '{"paperless":"documind-ingestion"}',
      async (cmd, args) => {
        calls.push([cmd, ...args]);
      },
    );
    const result = await service.restart("paperless");
    expect(result).toEqual({ namespace: "paperless", restarted: true });
    expect(calls).toEqual([["docker", "restart", "documind-ingestion"]]);
  });

  it("throws 502 when docker restart fails", async () => {
    const service = makeService(
      '{"paperless":"documind-ingestion"}',
      async () => {
        throw new Error("boom");
      },
    );
    const err = (await service.restart("paperless").catch((e) => e)) as HttpException;
    expect(err.getStatus()).toBe(HttpStatus.BAD_GATEWAY);
  });
});
