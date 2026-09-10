import { Injectable, HttpException, HttpStatus } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import type { SearchRequestDto, SearchResult } from '@documind/shared';

@Injectable()
export class RetrievalService {
  private readonly retrievalUrl =
    process.env.RETRIEVAL_PIPELINE_URL || 'http://localhost:8002';

  constructor(private httpService: HttpService) {}

  async search(dto: SearchRequestDto): Promise<SearchResult[]> {
    try {
      const response = await firstValueFrom(
        this.httpService.post(`${this.retrievalUrl}/search`, {
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

  async getContext(question: string, maxSources = 5) {
    try {
      const response = await firstValueFrom(
        this.httpService.post(`${this.retrievalUrl}/context`, {
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
    try {
      const response = await firstValueFrom(
        this.httpService.get(`${this.retrievalUrl}/status`),
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
