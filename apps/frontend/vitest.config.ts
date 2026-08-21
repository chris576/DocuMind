import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: [],
    coverage: {
      // Coverage wird berichtet; die harte 75%-Schwelle für die großen
      // UI-Apps wird erst mit der Container-/E2E-Infrastruktur aktiviert.
      provider: "v8",
      reporter: ["text", "text-summary"],
      include: ["src/**"],
    },
  },
});
