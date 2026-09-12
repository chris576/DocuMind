import { Controller, Get, Param, Post } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import { PipelineRegistry } from './pipeline-registry';
import { RestartService } from './restart.service';

@Controller('pipelines')
export class PipelinesController {
  constructor(
    private readonly registry: PipelineRegistry,
    private readonly httpService: HttpService,
    private readonly restartService: RestartService,
  ) {}

  @Get()
  list() {
    return {
      namespaces: this.registry.listNamespaces(),
      pipelines: this.registry.list(),
    };
  }

  @Get('status')
  async status() {
    const results = [];
    for (const pipeline of this.registry.list()) {
      results.push({
        namespace: pipeline.namespace,
        collection: pipeline.collection,
        ingestion: await this.fetchStatus(`${pipeline.ingestionUrl}/status`),
        retrieval: await this.fetchStatus(`${pipeline.retrievalUrl}/status`),
        generation: await this.fetchStatus(`${pipeline.generationUrl}/status`),
      });
    }
    return results;
  }

  @Post(':namespace/restart')
  restart(@Param('namespace') namespace: string) {
    return this.restartService.restart(namespace);
  }

  private async fetchStatus(url: string) {
    try {
      const response = await firstValueFrom(this.httpService.get(url));
      return response.data;
    } catch {
      return { status: 'unavailable' };
    }
  }
}
