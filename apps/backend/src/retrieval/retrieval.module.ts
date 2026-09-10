import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { RetrievalController } from './retrieval.controller';
import { RetrievalService } from './retrieval.service';

@Module({
  imports: [HttpModule],
  controllers: [RetrievalController],
  providers: [RetrievalService],
  exports: [RetrievalService],
})
export class RetrievalModule {}
