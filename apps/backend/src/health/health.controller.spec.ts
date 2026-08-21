import { describe, expect, it } from "vitest";

import { HealthController } from "./health.controller";

describe("HealthController", () => {
  const controller = new HealthController();

  it("returns ok status with service name", () => {
    const result = controller.check();
    expect(result.status).toBe("ok");
    expect(result.service).toBe("dms-rag-backend");
    expect(result.timestamp).toBeDefined();
  });
});
