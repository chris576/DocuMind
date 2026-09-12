import { Controller, Post, Get, Body, Res } from '@nestjs/common';
import { ApiTags, ApiOperation } from '@nestjs/swagger';
import type { Response } from 'express';
import { Readable } from 'node:stream';
import { GenerationService } from './generation.service';
import type {
  AskRequestDto,
  ChatInitRequestDto,
  ChatMessageRequestDto,
} from '@documind/shared';

@ApiTags('Generation')
@Controller('generation')
export class GenerationController {
  constructor(private readonly generationService: GenerationService) {}

  @Post('ask')
  @ApiOperation({ summary: 'Ask a question about documents' })
  async ask(@Body() dto: AskRequestDto) {
    return this.generationService.ask(dto);
  }

  @Post('ask/stream')
  @ApiOperation({ summary: 'Ask a question with streamed answer (SSE)' })
  async askStream(@Body() dto: AskRequestDto, @Res() res: Response) {
    const stream = await this.generationService.askStream(dto);
    this.pipeSse(res, stream);
  }

  @Get('status')
  @ApiOperation({ summary: 'Get generation pipeline status' })
  async getStatus() {
    return this.generationService.getStatus();
  }

  @Post('chat/init')
  @ApiOperation({ summary: 'Initialize a document chat' })
  async chatInit(@Body() dto: ChatInitRequestDto) {
    return this.generationService.chatInit(dto);
  }

  @Post('chat/message')
  @ApiOperation({ summary: 'Send a chat message' })
  async chatMessage(@Body() dto: ChatMessageRequestDto) {
    return this.generationService.chatMessage(dto);
  }

  @Post('chat/message/stream')
  @ApiOperation({ summary: 'Send a chat message with streamed response (SSE)' })
  async chatMessageStream(
    @Body() dto: ChatMessageRequestDto,
    @Res() res: Response,
  ) {
    const stream = await this.generationService.chatMessageStream(dto);
    this.pipeSse(res, stream);
  }

  private pipeSse(res: Response, stream: Readable) {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    stream.pipe(res as unknown as NodeJS.WritableStream);
  }
}
