import { Injectable, HttpException, HttpStatus } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import type { SearchRequestDto, AskQuestionDto } from '@paperless/shared';
import { MessagingService, PipelineRoutingKey } from '../messaging/messaging.service';

@Injectable()
export class RagService {
  private readonly retrievalUrl = process.env.RETRIEVAL_PIPELINE_URL || 'http://localhost:8002';
  private readonly generationUrl = process.env.GENERATION_PIPELINE_URL || 'http://localhost:8003';

  constructor(
    private httpService: HttpService,
    private messagingService: MessagingService,
  ) {}

  async search(dto: SearchRequestDto) {
    try {
      const response = await firstValueFrom(
        this.httpService.post(`${this.retrievalUrl}/search`, dto),
      );
      return response.data;
    } catch (error) {
      throw new HttpException(
        'RAG search failed',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  async ask(dto: AskQuestionDto) {
    try {
      // 1. Get context from retrieval pipeline
      const contextResponse = await firstValueFrom(
        this.httpService.post(`${this.retrievalUrl}/context`, {
          question: dto.question,
          max_sources: dto.maxSources || 5,
        }),
      );

      // 2. Generate answer with generation pipeline
      const generationResponse = await firstValueFrom(
        this.httpService.post(`${this.generationUrl}/generate`, {
          question: dto.question,
          context: contextResponse.data.context,
          sources: contextResponse.data.sources,
        }),
      );

      return {
        answer: generationResponse.data.answer,
        sources: contextResponse.data.sources,
        metrics: generationResponse.data.metrics,
      };
    } catch (error) {
      throw new HttpException(
        'RAG ask failed',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  async getStatus() {
    try {
      const [retrievalStatus, generationStatus] = await Promise.all([
        firstValueFrom(this.httpService.get(`${this.retrievalUrl}/status`)),
        firstValueFrom(this.httpService.get(`${this.generationUrl}/status`)),
      ]);

      return {
        retrieval: retrievalStatus.data,
        generation: generationStatus.data,
      };
    } catch (error) {
      return {
        retrieval: { status: 'unavailable' },
        generation: { status: 'unavailable' },
      };
    }
  }

  async startIndexing() {
    // Publish async ingestion message via RabbitMQ
    await this.messagingService.publish(PipelineRoutingKey.INGESTION, {
      action: 'ingest',
      check_new: true,
    });

    // Also trigger HTTP endpoint for immediate response
    try {
      const response = await firstValueFrom(
        this.httpService.post(`${process.env.INGESTION_PIPELINE_URL || 'http://localhost:8001'}/ingest`, {
          force: false,
          check_new: true,
        }),
      );
      return {
        ...response.data,
        rabbitmq: this.messagingService.isConnected(),
      };
    } catch (error) {
      // If HTTP fails but RabbitMQ is connected, still report success via queue
      if (this.messagingService.isConnected()) {
        return {
          status: 'queued',
          message: 'Indexing queued via RabbitMQ',
          rabbitmq: true,
        };
      }
      throw new HttpException(
        'Failed to start indexing',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  async getIndexStatus() {
    try {
      const response = await firstValueFrom(
        this.httpService.get(`${process.env.INGESTION_PIPELINE_URL || 'http://localhost:8001'}/status`),
      );
      return response.data;
    } catch (error) {
      throw new HttpException(
        'Failed to get indexing status',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }
}
