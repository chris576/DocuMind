import { vi } from "vitest";

// Minimal-Umgebung, damit das config-Modul beim Import (env = validateEnv())
// erfolgreich validiert. Das Schema verlangt PAPERLESS_API_URL + PAPERLESS_API_TOKEN;
// alle anderen Felder haben Defaults.
vi.stubEnv("PAPERLESS_API_URL", "http://paperless:8000");
vi.stubEnv("PAPERLESS_API_TOKEN", "tok");
