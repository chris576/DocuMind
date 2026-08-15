import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { ExternalApiController } from './external-api.controller';
import { ExternalApiService } from './external-api.service';
import { ExternalToken } from './entities/external-token.entity';
import { ExternalTokenUsage } from './entities/external-token-usage.entity';

@Module({
  imports: [
    TypeOrmModule.forFeature([ExternalToken, ExternalTokenUsage]),
  ],
  controllers: [ExternalApiController],
  providers: [ExternalApiService],
  exports: [ExternalApiService],
})
export class ExternalApiModule {}
