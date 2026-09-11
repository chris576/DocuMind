import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { PipelineRegistry } from './pipeline-registry';
import { RestartService } from './restart.service';
import { PipelinesController } from './pipelines.controller';

@Module({
  imports: [HttpModule],
  controllers: [PipelinesController],
  providers: [PipelineRegistry, RestartService],
  exports: [PipelineRegistry],
})
export class PipelinesModule {}
