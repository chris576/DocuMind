import { vi } from "vitest";

// Setze Minimal-Umgebung, damit das config-Modul beim Import (env = validateEnv())
// erfolgreich validiert. Wird nur in Tests verwendet.
vi.stubEnv("JWT_SECRET", "a".repeat(32));
vi.stubEnv("PAPERLESS_API_URL", "http://paperless:8000");
vi.stubEnv("PAPERLESS_API_TOKEN", "tok");
