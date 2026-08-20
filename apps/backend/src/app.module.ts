import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { AuthModule } from './auth/auth.module';
import { RagModule } from './rag/rag.module';
import { ChatModule } from './chat/chat.module';
import { DocumentsModule } from './documents/documents.module';
import { ExternalApiModule } from './external-api/external-api.module';
import { HealthModule } from './health/health.module';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: ['.env', '../../.env'],
    }),
    AuthModule,
    RagModule,
    ChatModule,
    DocumentsModule,
    ExternalApiModule,
    HealthModule,
  ],
})
export class AppModule {}
