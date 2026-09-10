import { Injectable, HttpException, HttpStatus } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import type { IngestionRunDto } from '@documind/shared';

@Injectable()
export class IngestionService {
  private readonly ingestionUrl =
    process.env.INGESTION_PIPELINE_URL || 'http://localhost:8001';

  constructor(private httpService: HttpService) {}

  async run(dto: IngestionRunDto) {
    try {
      const response = await firstValueFrom(
        this.httpService.post(`${this.ingestionUrl}/ingest`, {
          force: dto.force ?? false,
          check_new: dto.checkNew ?? false,
        }),
      );
      return response.data;
    } catch (error) {
      throw new HttpException(
        'Failed to start ingestion',
        HttpStatus.BAD_GATEWAY,
      );
    }
  }

  async runSync(dto: IngestionRunDto) {
    try {
      const response = await firstValueFrom(
        this.httpService.post(`${this.ingestionUrl}/ingest/sync`, {
          force: dto.force ?? false,
          check_new: dto.checkNew ?? false,
        }),
      );
      return response.data;
    } catch (error) {
      throw new HttpException('Ingestion failed', HttpStatus.BAD_GATEWAY);
    }
  }

  async getStatus() {
    try {
      const response = await firstValueFrom(
        this.httpService.get(`${this.ingestionUrl}/status`),
      );
      return response.data;
    } catch (error) {
      throw new HttpException(
        'Ingestion status unavailable',
        HttpStatus.BAD_GATEWAY,
      );
    }
  }
}
