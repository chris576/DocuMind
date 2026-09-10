import { Injectable, HttpException, HttpStatus } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import { Readable } from 'stream';
import type {
  AskRequestDto,
  AskResponseDto,
  ChatInitRequestDto,
  ChatMessageRequestDto,
} from '@documind/shared';

@Injectable()
export class GenerationService {
  private readonly generationUrl =
    process.env.GENERATION_PIPELINE_URL || 'http://localhost:8003';

  constructor(private httpService: HttpService) {}

  async ask(dto: AskRequestDto): Promise<AskResponseDto> {
    try {
      const response = await firstValueFrom(
        this.httpService.post(`${this.generationUrl}/generate`, {
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
      throw new HttpException('Generation failed', HttpStatus.BAD_GATEWAY);
    }
  }

  async askStream(dto: AskRequestDto): Promise<Readable> {
    try {
      const response = await firstValueFrom(
        this.httpService.post(
          `${this.generationUrl}/generate/stream`,
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
      throw new HttpException('Generation stream failed', HttpStatus.BAD_GATEWAY);
    }
  }

  async getStatus() {
    try {
      const response = await firstValueFrom(
        this.httpService.get(`${this.generationUrl}/status`),
      );
      return response.data;
    } catch (error) {
      throw new HttpException(
        'Generation status unavailable',
        HttpStatus.BAD_GATEWAY,
      );
    }
  }

  async chatInit(dto: ChatInitRequestDto) {
    try {
      const response = await firstValueFrom(
        this.httpService.post(`${this.generationUrl}/chat/init`, {
          document_id: dto.documentId,
          document_title: dto.documentTitle,
          document_content: dto.documentContent,
        }),
      );
      return response.data;
    } catch (error) {
      throw new HttpException(
        'Chat initialization failed',
        HttpStatus.BAD_GATEWAY,
      );
    }
  }

  async chatMessage(dto: ChatMessageRequestDto) {
    try {
      const response = await firstValueFrom(
        this.httpService.post(`${this.generationUrl}/chat/message`, {
          chat_id: dto.chatId,
          message: dto.message,
        }),
      );
      return response.data;
    } catch (error) {
      throw new HttpException('Chat message failed', HttpStatus.BAD_GATEWAY);
    }
  }

  async chatMessageStream(dto: ChatMessageRequestDto): Promise<Readable> {
    try {
      const response = await firstValueFrom(
        this.httpService.post(
          `${this.generationUrl}/chat/message/stream`,
          { chat_id: dto.chatId, message: dto.message },
          { responseType: 'stream' },
        ),
      );
      return response.data as Readable;
    } catch (error) {
      throw new HttpException('Chat stream failed', HttpStatus.BAD_GATEWAY);
    }
  }
}
