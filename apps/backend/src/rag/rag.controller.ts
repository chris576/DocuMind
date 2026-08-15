import { Controller, Post, Get, Body, UseGuards } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiBearerAuth } from '@nestjs/swagger';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { RagService } from './rag.service';
import { SearchRequestDto, AskQuestionDto } from '@paperless/shared';

@ApiTags('RAG')
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller('rag')
export class RagController {
  constructor(private ragService: RagService) {}

  @Post('search')
  @ApiOperation({ summary: 'Search documents' })
  async search(@Body() dto: SearchRequestDto) {
    return this.ragService.search(dto);
  }

  @Post('ask')
  @ApiOperation({ summary: 'Ask a question about documents' })
  async ask(@Body() dto: AskQuestionDto) {
    return this.ragService.ask(dto);
  }

  @Get('status')
  @ApiOperation({ summary: 'Get RAG service status' })
  async getStatus() {
    return this.ragService.getStatus();
  }

  @Post('index')
  @ApiOperation({ summary: 'Start document indexing' })
  async index() {
    return this.ragService.startIndexing();
  }

  @Get('index/status')
  @ApiOperation({ summary: 'Get indexing status' })
  async getIndexStatus() {
    return this.ragService.getIndexStatus();
  }
}
