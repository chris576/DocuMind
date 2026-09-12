import { HttpException, HttpStatus, Injectable, Optional } from '@nestjs/common';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

type RunCommand = (command: string, args: string[]) => Promise<unknown>;

const defaultRunCommand: RunCommand = (command, args) =>
  execFileAsync(command, args, { timeout: 30000 });

/**
 * Scoped restart control-plane. Restarts only containers explicitly mapped in
 * `PIPELINE_CONTAINER_MAP` (JSON: namespace → container name). The gateway
 * never exposes a generic command runner — the allowlist is the whole surface.
 */
@Injectable()
export class RestartService {
  private readonly containerMap: Record<string, string>;
  private readonly runCommand: RunCommand;

  constructor(@Optional() runCommand?: RunCommand) {
    this.containerMap = this.parseMap(process.env.PIPELINE_CONTAINER_MAP);
    this.runCommand = runCommand ?? defaultRunCommand;
  }

  async restart(namespace: string): Promise<{ namespace: string; restarted: boolean }> {
    const container = this.containerMap[namespace];
    if (!container) {
      throw new HttpException(
        `No container mapped for namespace "${namespace}" (PIPELINE_CONTAINER_MAP)`,
        HttpStatus.NOT_IMPLEMENTED,
      );
    }

    try {
      await this.runCommand('docker', ['restart', container]);
      return { namespace, restarted: true };
    } catch (error) {
      throw new HttpException(
        `Failed to restart container "${container}": ${(error as Error).message}`,
        HttpStatus.BAD_GATEWAY,
      );
    }
  }

  private parseMap(raw?: string): Record<string, string> {
    if (!raw) {
      return {};
    }
    try {
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === 'object' ? (parsed as Record<string, string>) : {};
    } catch {
      return {};
    }
  }
}
