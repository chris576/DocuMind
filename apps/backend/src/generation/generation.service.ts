import { Injectable, HttpException, HttpStatus, Logger } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import { Readable } from 'node:stream';
import type {
  AskRequestDto,
  AskResponseDto,
  ChatInitRequestDto,
  ChatMessageRequestDto,
} from '@documind/shared';
import {
  PipelineRegistry,
  type ResolvedPipeline,
} from '../pipelines/pipeline-registry';

@Injectable()
export class GenerationService {
  private readonly logger = new Logger(GenerationService.name);

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

  async ask(dto: AskRequestDto): Promise<AskResponseDto> {
    const pipeline = this.resolve(dto.namespace);
    try {
      const response = await firstValueFrom(
        this.httpService.post(`${pipeline.generationUrl}/generate`, {
          question: dto.question,
          max_tokens: dto.maxTokens,
          temperature: dto.temperature,
        }),
      );
      const data = response.data;
      return {
        answer: data.answer,
        sources: [],
        metrics: {
          promptTokens: data.prompt_tokens,
          completionTokens: data.completion_tokens,
          totalTokens: data.total_tokens,
        },
        model: data.model,
        provider: data.provider,
      };
    } catch (error) {
      this.logger.error(
        `Generation failed: ${(error as Error).message}`,
        (error as Error).stack,
      );
      throw new HttpException('Generation failed', HttpStatus.BAD_GATEWAY, {
        cause: error,
      });
    }
  }

  async askStream(dto: AskRequestDto): Promise<Readable> {
    const pipeline = this.resolve(dto.namespace);
    try {
      const response = await firstValueFrom(
        this.httpService.post(
          `${pipeline.generationUrl}/generate/stream`,
          {
            question: dto.question,
            max_tokens: dto.maxTokens,
            temperature: dto.temperature,
          },
          { responseType: 'stream' },
        ),
      );
      return response.data as Readable;
    } catch (error) {
      this.logger.error(
        `Generation stream failed: ${(error as Error).message}`,
        (error as Error).stack,
      );
      throw new HttpException(
        'Generation stream failed',
        HttpStatus.BAD_GATEWAY,
        { cause: error },
      );
    }
  }

  async getStatus() {
    const pipeline = this.resolve();
    try {
      const response = await firstValueFrom(
        this.httpService.get(`${pipeline.generationUrl}/status`),
      );
      return response.data;
    } catch (error) {
      this.logger.error(
        `Generation status unavailable: ${(error as Error).message}`,
        (error as Error).stack,
      );
      throw new HttpException(
        'Generation status unavailable',
        HttpStatus.BAD_GATEWAY,
        { cause: error },
      );
    }
  }

  async chatInit(dto: ChatInitRequestDto) {
    const pipeline = this.resolve(dto.namespace);
    try {
      const response = await firstValueFrom(
        this.httpService.post(`${pipeline.generationUrl}/chat/init`, {
          document_id: dto.documentId,
          document_title: dto.documentTitle,
          document_content: dto.documentContent,
        }),
      );
      return response.data;
    } catch (error) {
      this.logger.error(
        `Chat initialization failed: ${(error as Error).message}`,
        (error as Error).stack,
      );
      throw new HttpException(
        'Chat initialization failed',
        HttpStatus.BAD_GATEWAY,
        { cause: error },
      );
    }
  }

  async chatMessage(dto: ChatMessageRequestDto) {
    const pipeline = this.resolve(dto.namespace);
    try {
      const response = await firstValueFrom(
        this.httpService.post(`${pipeline.generationUrl}/chat/message`, {
          chat_id: dto.chatId,
          message: dto.message,
        }),
      );
      return response.data;
    } catch (error) {
      this.logger.error(
        `Chat message failed: ${(error as Error).message}`,
        (error as Error).stack,
      );
      throw new HttpException('Chat message failed', HttpStatus.BAD_GATEWAY, {
        cause: error,
      });
    }
  }

  async chatMessageStream(dto: ChatMessageRequestDto): Promise<Readable> {
    const pipeline = this.resolve(dto.namespace);
    try {
      const response = await firstValueFrom(
        this.httpService.post(
          `${pipeline.generationUrl}/chat/message/stream`,
          { chat_id: dto.chatId, message: dto.message },
          { responseType: 'stream' },
        ),
      );
      return response.data as Readable;
    } catch (error) {
      this.logger.error(
        `Chat stream failed: ${(error as Error).message}`,
        (error as Error).stack,
      );
      throw new HttpException('Chat stream failed', HttpStatus.BAD_GATEWAY, {
        cause: error,
      });
    }
  }
}
