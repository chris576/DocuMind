import { Injectable, HttpException, HttpStatus, Logger } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import type { IngestionRunDto } from '@documind/shared';
import {
  PipelineRegistry,
  type ResolvedPipeline,
} from '../pipelines/pipeline-registry';
import { IngestionJob, IngestionJobStore } from './job-store';

@Injectable()
export class IngestionService {
  private readonly logger = new Logger(IngestionService.name);

  constructor(
    private readonly httpService: HttpService,
    private readonly registry: PipelineRegistry,
    private readonly jobStore: IngestionJobStore,
  ) {}

  private resolve(namespace?: string): ResolvedPipeline {
    try {
      return this.registry.resolve(namespace);
    } catch (error) {
      throw new HttpException(
        (error as Error).message,
        HttpStatus.BAD_REQUEST,
      );
    }
  }

  async run(dto: IngestionRunDto): Promise<IngestionJob> {
    const pipeline = this.resolve(dto.namespace);
    const job = this.jobStore.create(pipeline.namespace);

    try {
      const response = await firstValueFrom(
        this.httpService.post(`${pipeline.ingestionUrl}/ingest`, {
          force: dto.force ?? false,
          check_new: dto.checkNew ?? false,
        }),
      );
      this.jobStore.update(job.id, {
        status: 'running',
        message: response.data?.message,
      });
      return this.jobStore.get(job.id) ?? job;
    } catch (error) {
      this.jobStore.update(job.id, { status: 'failed' });
      this.logger.error(
        `Failed to start ingestion: ${(error as Error).message}`,
        (error as Error).stack,
      );
      throw new HttpException(
        'Failed to start ingestion',
        HttpStatus.BAD_GATEWAY,
        { cause: error },
      );
    }
  }

  async runSync(dto: IngestionRunDto) {
    const pipeline = this.resolve(dto.namespace);
    try {
      const response = await firstValueFrom(
        this.httpService.post(`${pipeline.ingestionUrl}/ingest/sync`, {
          force: dto.force ?? false,
          check_new: dto.checkNew ?? false,
        }),
      );
      return response.data;
    } catch (error) {
      this.logger.error(
        `Ingestion failed: ${(error as Error).message}`,
        (error as Error).stack,
      );
      throw new HttpException('Ingestion failed', HttpStatus.BAD_GATEWAY, {
        cause: error,
      });
    }
  }

  async getStatus() {
    const pipeline = this.resolve();
    try {
      const response = await firstValueFrom(
        this.httpService.get(`${pipeline.ingestionUrl}/status`),
      );
      return response.data;
    } catch (error) {
      this.logger.error(
        `Ingestion status unavailable: ${(error as Error).message}`,
        (error as Error).stack,
      );
      throw new HttpException(
        'Ingestion status unavailable',
        HttpStatus.BAD_GATEWAY,
        { cause: error },
      );
    }
  }

  async getJob(id: string): Promise<IngestionJob> {
    const job = this.jobStore.get(id);
    if (!job) {
      throw new HttpException('Job not found', HttpStatus.NOT_FOUND);
    }
    return this.refreshJob(job);
  }

  async listJobs(): Promise<IngestionJob[]> {
    const jobs = this.jobStore.list();
    return Promise.all(jobs.map((job) => this.refreshJob(job)));
  }

  private async refreshJob(job: IngestionJob): Promise<IngestionJob> {
    if (job.status !== 'running') {
      return job;
    }
    try {
      const pipeline = this.resolve(job.namespace);
      const response = await firstValueFrom(
        this.httpService.get(`${pipeline.ingestionUrl}/status`),
      );
      if (response.data?.running === false) {
        this.jobStore.update(job.id, { status: 'completed' });
      }
    } catch {
      // Keep the current status when the pipeline is unreachable.
    }
    return this.jobStore.get(job.id) ?? job;
  }
}
