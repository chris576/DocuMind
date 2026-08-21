import { defineConfig } from "vitest/config";

// Root Vitest-Workspace-Config.
// Jedes Paket/App steuert seine eigene vitest.config.ts bei; hier werden
// gemeinsame Defaults gesetzt, die per Projekt überschrieben werden können.
export default defineConfig({
  test: {
    passWithNoTests: true,
  },
});
