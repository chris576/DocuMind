import { afterEach, describe, expect, it } from "vitest";
import { GatewayAuthGuard } from "./gateway-auth.guard";

function contextWith(path: string, authorization?: string) {
  return {
    switchToHttp: () => ({
      getRequest: () => ({
        path,
        headers: authorization ? { authorization } : {},
      }),
    }),
  } as any;
}

describe("GatewayAuthGuard", () => {
  const originalToken = process.env.GATEWAY_API_TOKEN;

  afterEach(() => {
    if (originalToken === undefined) {
      delete process.env.GATEWAY_API_TOKEN;
    } else {
      process.env.GATEWAY_API_TOKEN = originalToken;
    }
  });

  it("allows everything when no token is configured", () => {
    delete process.env.GATEWAY_API_TOKEN;
    const guard = new GatewayAuthGuard();
    expect(guard.canActivate(contextWith("/api/ingestion/run"))).toBe(true);
  });

  it("rejects a protected route without authorization", () => {
    process.env.GATEWAY_API_TOKEN = "secret";
    const guard = new GatewayAuthGuard();
    expect(guard.canActivate(contextWith("/api/ingestion/run"))).toBe(false);
  });

  it("rejects a wrong token", () => {
    process.env.GATEWAY_API_TOKEN = "secret";
    const guard = new GatewayAuthGuard();
    expect(
      guard.canActivate(contextWith("/api/ingestion/run", "Bearer wrong")),
    ).toBe(false);
  });

  it("allows a valid bearer token", () => {
    process.env.GATEWAY_API_TOKEN = "secret";
    const guard = new GatewayAuthGuard();
    expect(
      guard.canActivate(contextWith("/api/ingestion/run", "Bearer secret")),
    ).toBe(true);
  });

  it("allows /api/health without a token", () => {
    process.env.GATEWAY_API_TOKEN = "secret";
    const guard = new GatewayAuthGuard();
    expect(guard.canActivate(contextWith("/api/health"))).toBe(true);
  });

  it("allows non-/api paths (swagger) without a token", () => {
    process.env.GATEWAY_API_TOKEN = "secret";
    const guard = new GatewayAuthGuard();
    expect(guard.canActivate(contextWith("/api-docs"))).toBe(true);
  });
});
