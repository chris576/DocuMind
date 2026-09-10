import { Controller, Post, Get, Body } from '@nestjs/common';
import { ApiTags, ApiOperation } from '@nestjs/swagger';
import { IngestionService } from './ingestion.service';
import type { IngestionRunDto } from '@documind/shared';

@ApiTags('Ingestion')
@Controller('ingestion')
export class IngestionController {
  constructor(private ingestionService: IngestionService) {}

  @Post('run')
  @ApiOperation({ summary: 'Start document indexing (background)' })
  async run(@Body() dto: IngestionRunDto) {
    return this.ingestionService.run(dto);
  }

  @Post('run/sync')
  @ApiOperation({ summary: 'Run document indexing synchronously' })
  async runSync(@Body() dto: IngestionRunDto) {
    return this.ingestionService.runSync(dto);
  }

  @Get('status')
  @ApiOperation({ summary: 'Get indexing status' })
  async getStatus() {
    return this.ingestionService.getStatus();
  }
}
