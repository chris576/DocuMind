import { Controller, Post, Body, UseGuards, Sse, MessageEvent } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiBearerAuth } from '@nestjs/swagger';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { ChatService } from './chat.service';
import { ChatInitDto, ChatMessageDto } from '@paperless/shared';
import { Observable, map } from 'rxjs';

@ApiTags('Chat')
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller('chat')
export class ChatController {
  constructor(private chatService: ChatService) {}

  @Post('init')
  @ApiOperation({ summary: 'Initialize chat for a document' })
  async init(@Body() dto: ChatInitDto) {
    return this.chatService.initializeChat(dto.documentId);
  }

  @Sse('message')
  @ApiOperation({ summary: 'Send message to document chat (SSE)' })
  async message(@Body() dto: ChatMessageDto): Promise<Observable<MessageEvent>> {
    const stream = await this.chatService.sendMessageStream(dto.documentId, dto.message);
    
    return new Observable<MessageEvent>((subscriber) => {
      stream.on('data', (chunk: string) => {
        subscriber.next({ data: chunk } as MessageEvent);
      });
      
      stream.on('end', () => {
        subscriber.complete();
      });
      
      stream.on('error', (error: Error) => {
        subscriber.error(error);
      });
    });
  }
}
