import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    exclude: ["node_modules/**", "dist/**", "coverage/**", ".git/**"],
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
