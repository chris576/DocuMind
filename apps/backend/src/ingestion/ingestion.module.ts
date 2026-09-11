import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { IngestionController } from './ingestion.controller';
import { IngestionService } from './ingestion.service';
import { IngestionJobStore } from './job-store';
import { PipelinesModule } from '../pipelines/pipelines.module';

@Module({
  imports: [HttpModule, PipelinesModule],
  controllers: [IngestionController],
  providers: [IngestionService, IngestionJobStore],
  exports: [IngestionService],
})
export class IngestionModule {}
