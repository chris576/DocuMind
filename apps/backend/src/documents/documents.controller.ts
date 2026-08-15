import { Controller, Get, Post, Body, Param, UseGuards } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiBearerAuth } from '@nestjs/swagger';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { DocumentsService } from './documents.service';

@ApiTags('Documents')
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller('documents')
export class DocumentsController {
  constructor(private documentsService: DocumentsService) {}

  @Get()
  @ApiOperation({ summary: 'Get all documents' })
  async findAll() {
    return this.documentsService.findAll();
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get document by ID' })
  async findOne(@Param('id') id: string) {
    return this.documentsService.findOne(parseInt(id, 10));
  }

  @Post(':id/process')
  @ApiOperation({ summary: 'Process document with AI' })
  async process(@Param('id') id: string) {
    return this.documentsService.processDocument(parseInt(id, 10));
  }

  @Get(':id/content')
  @ApiOperation({ summary: 'Get document content' })
  async getContent(@Param('id') id: string) {
    return this.documentsService.getContent(parseInt(id, 10));
  }
}
