import { Injectable, HttpException, HttpStatus } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import { Readable } from 'stream';

@Injectable()
export class ChatService {
  private readonly generationUrl = process.env.GENERATION_PIPELINE_URL || 'http://localhost:8003';

  constructor(private httpService: HttpService) {}

  async initializeChat(documentId: number) {
    try {
      const response = await firstValueFrom(
        this.httpService.post(`${this.generationUrl}/chat/init`, { documentId }),
      );
      return response.data;
    } catch (error) {
      throw new HttpException(
        'Failed to initialize chat',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  async sendMessageStream(documentId: number, message: string): Promise<Readable> {
    try {
      const response = await firstValueFrom(
        this.httpService.post(
          `${this.generationUrl}/chat/message`,
          { documentId, message },
          { responseType: 'stream' },
        ),
      );
      return response.data;
    } catch (error) {
      throw new HttpException(
        'Failed to send chat message',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }
}
