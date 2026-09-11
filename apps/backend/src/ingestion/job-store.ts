import { Injectable } from '@nestjs/common';
import { randomUUID } from 'crypto';

export type JobStatus = 'queued' | 'running' | 'completed' | 'failed';

export interface IngestionJob {
  id: string;
  namespace: string;
  status: JobStatus;
  createdAt: string;
  updatedAt: string;
  message?: string;
}

/**
 * In-memory ingestion job registry. v1 keeps jobs only for the lifetime of the
 * gateway process; a Redis-backed store can replace it later without touching
 * the service/controller contract.
 */
@Injectable()
export class IngestionJobStore {
  private readonly jobs = new Map<string, IngestionJob>();

  create(namespace: string): IngestionJob {
    const now = new Date().toISOString();
    const job: IngestionJob = {
      id: randomUUID(),
      namespace,
      status: 'queued',
      createdAt: now,
      updatedAt: now,
    };
    this.jobs.set(job.id, job);
    return job;
  }

  get(id: string): IngestionJob | undefined {
    return this.jobs.get(id);
  }

  list(): IngestionJob[] {
    return [...this.jobs.values()].sort((a, b) =>
      b.createdAt.localeCompare(a.createdAt),
    );
  }

  update(id: string, patch: Partial<IngestionJob>): IngestionJob | undefined {
    const job = this.jobs.get(id);
    if (!job) {
      return undefined;
    }
    Object.assign(job, patch, { updatedAt: new Date().toISOString() });
    return job;
  }
}
