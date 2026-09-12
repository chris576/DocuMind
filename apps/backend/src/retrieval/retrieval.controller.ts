import { Controller, Post, Get, Body } from '@nestjs/common';
import { ApiTags, ApiOperation } from '@nestjs/swagger';
import { RetrievalService } from './retrieval.service';
import type { SearchRequestDto } from '@documind/shared';

@ApiTags('Retrieval')
@Controller('retrieval')
export class RetrievalController {
  constructor(private readonly retrievalService: RetrievalService) {}

  @Post('search')
  @ApiOperation({ summary: 'Search documents' })
  async search(@Body() dto: SearchRequestDto) {
    return this.retrievalService.search(dto);
  }

  @Post('context')
  @ApiOperation({ summary: 'Build retrieval context for a question' })
  async getContext(
    @Body()
    body: {
      question: string;
      maxSources?: number;
      namespace?: string;
      collections?: string[];
    },
  ) {
    return this.retrievalService.getContext(
      body.question,
      body.maxSources,
      body.namespace,
      body.collections,
    );
  }

  @Get('status')
  @ApiOperation({ summary: 'Get retrieval pipeline status' })
  async getStatus() {
    return this.retrievalService.getStatus();
  }
}
