import { Injectable, HttpException, HttpStatus, Logger } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import type { SearchRequestDto, SearchResult } from '@documind/shared';
import {
  PipelineRegistry,
  type ResolvedPipeline,
} from '../pipelines/pipeline-registry';

@Injectable()
export class RetrievalService {
  private readonly logger = new Logger(RetrievalService.name);

  constructor(
    private readonly httpService: HttpService,
    private readonly registry: PipelineRegistry,
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

  async search(dto: SearchRequestDto): Promise<SearchResult[]> {
    const pipeline = this.resolve(dto.namespace);
    try {
      const body: Record<string, unknown> = {
        query: dto.query,
        from_date: dto.fromDate,
        to_date: dto.toDate,
        correspondent: dto.correspondent,
        max_results: dto.maxResults ?? 20,
      };
      if (dto.collections && dto.collections.length > 0) {
        body.collections = dto.collections;
      }
      const response = await firstValueFrom(
        this.httpService.post(`${pipeline.retrievalUrl}/search`, body),
      );
      return this.mapResults(response.data);
    } catch (error) {
      this.logger.error(
        `Search failed: ${(error as Error).message}`,
        (error as Error).stack,
      );
      throw new HttpException('Search failed', HttpStatus.BAD_GATEWAY, {
        cause: error,
      });
    }
  }

  async getContext(
    question: string,
    maxSources = 5,
    namespace?: string,
    collections?: string[],
  ) {
    const pipeline = this.resolve(namespace);
    try {
      const body: Record<string, unknown> = {
        question,
        max_sources: maxSources,
      };
      if (collections && collections.length > 0) {
        body.collections = collections;
      }
      const response = await firstValueFrom(
        this.httpService.post(`${pipeline.retrievalUrl}/context`, body),
      );
      return response.data;
    } catch (error) {
      this.logger.error(
        `Context retrieval failed: ${(error as Error).message}`,
        (error as Error).stack,
      );
      throw new HttpException(
        'Context retrieval failed',
        HttpStatus.BAD_GATEWAY,
        { cause: error },
      );
    }
  }

  async getStatus() {
    const pipeline = this.resolve();
    try {
      const response = await firstValueFrom(
        this.httpService.get(`${pipeline.retrievalUrl}/status`),
      );
      return response.data;
    } catch (error) {
      this.logger.error(
        `Retrieval status unavailable: ${(error as Error).message}`,
        (error as Error).stack,
      );
      throw new HttpException(
        'Retrieval status unavailable',
        HttpStatus.BAD_GATEWAY,
        { cause: error },
      );
    }
  }

  private mapResults(results: unknown): SearchResult[] {
    const list = Array.isArray(results) ? results : [];
    return list.map((r: any) => ({
      title: r.title ?? '',
      correspondent: r.correspondent ?? '',
      date: r.date ?? '',
      score: r.score ?? 0,
      crossScore: r.cross_score ?? 0,
      snippet: r.snippet ?? '',
      docId: r.doc_id ?? undefined,
    }));
  }
}
