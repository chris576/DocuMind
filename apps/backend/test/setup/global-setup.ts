import { spawn, type ChildProcess } from 'node:child_process';
import { readFileSync, unlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = fileURLToPath(new URL('.', import.meta.url)); // .../apps/backend/test/setup/
const REPO_ROOT = resolve(HERE, '..', '..', '..', '..'); // Repo-Root
const PID_FILE = resolve(tmpdir(), 'dms-rag-integration.pids');

const HARNESSES = [
  { script: 'ingestion_harness.py', port: 8001 },
  { script: 'retrieval_harness.py', port: 8002 },
  { script: 'generation_harness.py', port: 8003 },
];

async function waitForHealth(url: string, timeoutMs = 60_000): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  let lastError: unknown = null;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${url}/health`);
      if (res.ok) return;
    } catch (error) {
      lastError = error;
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(
    `Health-Check fehlgeschlagen für ${url}: ${String(lastError)}`
  );
}

function killChildren(): void {
  try {
    const pids = readFileSync(PID_FILE, 'utf8').split('\n').filter(Boolean);
    for (const pid of pids) {
      const numeric = Number(pid);
      if (!Number.isFinite(numeric)) continue;
      try {
        process.kill(numeric, 'SIGKILL');
      } catch {
        // Prozess bereits beendet
      }
    }
  } catch {
    // Keine PID-Datei vorhanden — nichts zu tun
  }
  try {
    unlinkSync(PID_FILE);
  } catch {
    // bereits entfernt
  }
}

// Vitest 4 kennt kein separates globalTeardown — die Setup-Funktion gibt die
// Teardown-Funktion zurück.
export default async function setup(): Promise<() => void> {
  const python = resolve(REPO_ROOT, '.venv', 'bin', 'python');
  const children: ChildProcess[] = [];

  for (const h of HARNESSES) {
    const child = spawn(
      python,
      [resolve(REPO_ROOT, 'integration', 'harness', h.script)],
      {
        env: { ...process.env, PORT: String(h.port) },
        stdio: 'ignore',
      }
    );
    // Nicht auf die Subprozesse warten — sonst hält ihr Handle den
    // Vitest-Prozess beim Beenden auf ("close timed out").
    child.unref();
    children.push(child);
  }

  try {
    for (const h of HARNESSES) {
      await waitForHealth(`http://127.0.0.1:${h.port}`);
    }
  } catch (error) {
    for (const child of children) child.kill('SIGKILL');
    throw error;
  }

  writeFileSync(PID_FILE, children.map((c) => c.pid).join('\n'));

  return killChildren;
}
