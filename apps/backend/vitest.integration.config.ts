import swc from 'unplugin-swc';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  // SWC emittiert Decorator-Metadata (emitDecoratorMetadata) — nötig für
  // NestJS-DI unter Vitest (esbuild tut das nicht).
  plugins: [swc.vite()],
  test: {
    globals: true,
    environment: 'node',
    globalSetup: ['./test/setup/global-setup.ts'],
    // Nur die e2e-Specs ausführen (Unit-Tests laufen über die Standard-Config).
    include: ['test/**/*.e2e-spec.ts'],
    testTimeout: 30_000,
    hookTimeout: 120_000,
  },
});
