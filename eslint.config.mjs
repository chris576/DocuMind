import globals from "globals";
import pluginJs from "@eslint/js";
import prettier from "eslint-config-prettier";
import sonarjs from "eslint-plugin-sonarjs";

// HINWEIS zur statischen TS-Analyse:
// ---------------------------------------------------------------------------
// Das Monorepo nutzt TypeScript 7 (nativer Go-Compiler) im Root und in den
// TS-Paketen (siehe /memories/repo/build-facts.md). typescript-eslint /
// @typescript-eslint/parser unterstützen TS7 derzeit NICHT und werfen beim
// Laden "typescript-eslint does not support TS 7.0" (Issue #10940).
//
// Konsequenz:
//   - ESLint wird hier für JS/MJS/CJS-Dateien + sonarjs-Clean-Code-Regeln auf
//     JS-Quellen verwendet.
//   - Die statische .ts-Analyse (Clean Code + Typen) übernimmt das validierte
//     `tsc --noEmit` (typecheck) pro Paket; typ-basierte ESLint-Regeln können
//     ergänzt werden, sobald typescript-eslint TS>=7.1 unterstützt.
// ---------------------------------------------------------------------------
/** @type {import('eslint').Linter.Config[]} */
export default [
  {
    ignores: [
      "**/dist/**",
      "**/build/**",
      "**/coverage/**",
      "**/node_modules/**",
      "**/.turbo/**",
      // TS wird statisch über `tsc --noEmit` geprüft (typescript-eslint
      // unterstützt TS7 derzeit nicht). ESLint überspringt daher alle
      // TypeScript-Quellen.
      "**/*.ts",
      "**/*.tsx",
    ],
  },
  {
    files: ["**/*.js", "**/*.mjs", "**/*.cjs"],
    languageOptions: {
      sourceType: "module",
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    plugins: {
      sonarjs,
    },
    rules: {
      // Clean-Code-Kern: Komplexität begrenzen
      "complexity": ["error", { max: 12 }],
      "sonarjs/no-small-switch": "warn",
      "sonarjs/no-duplicate-string": "warn",
      "sonarjs/no-identical-functions": "warn",
      "sonarjs/cognitive-complexity": ["warn", 20],
      "sonarjs/no-collapsible-if": "warn",
      "sonarjs/no-extra-arguments": "warn",
    },
  },
  pluginJs.configs.recommended,
  prettier, // Prettier integriert
];
