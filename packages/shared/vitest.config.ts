import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    globals: true,
    coverage: {
      provider: "v8",
      reporter: ["text", "text-summary"],
      include: ["src/**"],
      thresholds: {
        lines: 75,
        functions: 75,
        statements: 75,
      },
    },
  },
});
