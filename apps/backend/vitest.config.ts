import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    globals: true,
    environment: "node",
    coverage: {
      // Bessere Android-Umgebung für die Nest-basierte Integration, sonst .coverage
      provider: "v8",
      reporter: ["text", "text-summary"],
      include: ["src/**"],
    },
  },
});
