import { Injectable, HttpException, HttpStatus } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import type { SearchRequestDto, SearchResult } from '@documind/shared';
import {
  PipelineRegistry,
  type ResolvedPipeline,
} from '../pipelines/pipeline-registry';

@Injectable()
export class RetrievalService {
  constructor(
    private httpService: HttpService,
    private registry: PipelineRegistry,
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
      const response = await firstValueFrom(
        this.httpService.post(`${pipeline.retrievalUrl}/search`, {
          query: dto.query,
          from_date: dto.fromDate,
          to_date: dto.toDate,
          correspondent: dto.correspondent,
          max_results: dto.maxResults ?? 20,
        }),
      );
      return this.mapResults(response.data);
    } catch (error) {
      throw new HttpException('Search failed', HttpStatus.BAD_GATEWAY);
    }
  }

  async getContext(question: string, maxSources = 5, namespace?: string) {
    const pipeline = this.resolve(namespace);
    try {
      const response = await firstValueFrom(
        this.httpService.post(`${pipeline.retrievalUrl}/context`, {
          question,
          max_sources: maxSources,
        }),
      );
      return response.data;
    } catch (error) {
      throw new HttpException(
        'Context retrieval failed',
        HttpStatus.BAD_GATEWAY,
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
      throw new HttpException(
        'Retrieval status unavailable',
        HttpStatus.BAD_GATEWAY,
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
