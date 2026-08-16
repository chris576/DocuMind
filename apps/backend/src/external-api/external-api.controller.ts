import { Controller, Post, Get, Delete, Body, Param, UseGuards, Request, HttpCode, HttpStatus } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiBearerAuth } from '@nestjs/swagger';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { ExternalApiService } from './external-api.service';
import type { CreateTokenDto } from '@paperless/shared';

@ApiTags('External API Tokens')
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller('external-api/tokens')
export class ExternalApiController {
  constructor(private externalApiService: ExternalApiService) {}

  @Post()
  @ApiOperation({ summary: 'Create a new external API token' })
  async create(@Request() req, @Body() dto: CreateTokenDto) {
    return this.externalApiService.createToken(req.user.id, dto);
  }

  @Get()
  @ApiOperation({ summary: 'List all tokens for current user' })
  async findAll(@Request() req) {
    return this.externalApiService.findAllByUser(req.user.id);
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get token by ID' })
  async findOne(@Request() req, @Param('id') id: string) {
    return this.externalApiService.findOne(parseInt(id, 10), req.user.id);
  }

  @Delete(':id')
  @HttpCode(HttpStatus.NO_CONTENT)
  @ApiOperation({ summary: 'Delete a token' })
  async remove(@Request() req, @Param('id') id: string) {
    return this.externalApiService.remove(parseInt(id, 10), req.user.id);
  }

  @Post(':id/revoke')
  @ApiOperation({ summary: 'Revoke a token' })
  async revoke(@Request() req, @Param('id') id: string) {
    return this.externalApiService.revoke(parseInt(id, 10), req.user.id);
  }

  @Post(':id/rotate')
  @ApiOperation({ summary: 'Rotate a token (create new, revoke old)' })
  async rotate(@Request() req, @Param('id') id: string) {
    return this.externalApiService.rotate(parseInt(id, 10), req.user.id);
  }

  @Get(':id/usage')
  @ApiOperation({ summary: 'Get usage statistics for a token' })
  async getUsage(@Request() req, @Param('id') id: string) {
    return this.externalApiService.getUsage(parseInt(id, 10), req.user.id);
  }
}
