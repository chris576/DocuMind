import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { GenerationController } from './generation.controller';
import { GenerationService } from './generation.service';
import { PipelinesModule } from '../pipelines/pipelines.module';

@Module({
  imports: [HttpModule, PipelinesModule],
  controllers: [GenerationController],
  providers: [GenerationService],
  exports: [GenerationService],
})
export class GenerationModule {}
