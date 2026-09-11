import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { RetrievalController } from './retrieval.controller';
import { RetrievalService } from './retrieval.service';
import { PipelinesModule } from '../pipelines/pipelines.module';

@Module({
  imports: [HttpModule, PipelinesModule],
  controllers: [RetrievalController],
  providers: [RetrievalService],
  exports: [RetrievalService],
})
export class RetrievalModule {}
