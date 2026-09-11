import { of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { PipelineRegistry } from './pipeline-registry';
import { PipelinesController } from './pipelines.controller';
import type { RestartService } from './restart.service';

const PIPELINES = [
  {
    namespace: 'paperless',
    collection: 'paperless',
    ingestionUrl: 'http://ing:8001',
    retrievalUrl: 'http://ret:8002',
    generationUrl: 'http://gen:8003',
  },
];

describe('PipelinesController', () => {
  const registry = { list: vi.fn(), listNamespaces: vi.fn() };
  const httpService = { get: vi.fn() };
  const restartService = { restart: vi.fn() };
  let controller: PipelinesController;

  beforeEach(() => {
    vi.clearAllMocks();
    registry.list.mockReturnValue(PIPELINES);
    registry.listNamespaces.mockReturnValue(['paperless']);

    controller = new PipelinesController(
      registry as unknown as PipelineRegistry,
      httpService as never,
      restartService as unknown as RestartService,
    );
  });

  it('listet Namespaces und Pipelines auf', () => {
    const result = controller.list();

    expect(result.namespaces).toEqual(['paperless']);
    expect(result.pipelines).toEqual(PIPELINES);
  });

  it('aggregiert die /status-Antworten aller Pipeline-Stufen', async () => {
    httpService.get.mockImplementation((url: string) =>
      of({ data: { from: url } }),
    );

    const result = await controller.status();

    expect(httpService.get).toHaveBeenCalledTimes(3);
    expect(httpService.get).toHaveBeenCalledWith('http://ing:8001/status');
    expect(httpService.get).toHaveBeenCalledWith('http://ret:8002/status');
    expect(httpService.get).toHaveBeenCalledWith('http://gen:8003/status');
    expect(result).toEqual([
      {
        namespace: 'paperless',
        collection: 'paperless',
        ingestion: { from: 'http://ing:8001/status' },
        retrieval: { from: 'http://ret:8002/status' },
        generation: { from: 'http://gen:8003/status' },
      },
    ]);
  });

  it('markiert nicht erreichbare Stufen als unavailable', async () => {
    httpService.get.mockImplementation((url: string) =>
      url.includes('ret')
        ? throwError(() => new Error('ECONNREFUSED'))
        : of({ data: { status: 'ok' } }),
    );

    const result = await controller.status();

    expect(result[0].retrieval).toEqual({ status: 'unavailable' });
    expect(result[0].ingestion).toEqual({ status: 'ok' });
    expect(result[0].generation).toEqual({ status: 'ok' });
  });

  it('aggregiert den Status über mehrere Namespaces hinweg', async () => {
    const second = {
      namespace: 'obs_vault',
      collection: 'obs_vault',
      ingestionUrl: 'http://ing2:8001',
      retrievalUrl: 'http://ret2:8002',
      generationUrl: 'http://gen2:8003',
    };
    registry.list.mockReturnValue([...PIPELINES, second]);
    httpService.get.mockImplementation(() => of({ data: {} }));

    const result = await controller.status();

    expect(result.map((p) => p.namespace)).toEqual(['paperless', 'obs_vault']);
    expect(httpService.get).toHaveBeenCalledTimes(6);
    expect(httpService.get).toHaveBeenCalledWith('http://ing2:8001/status');
  });

  it('delegiert Restarts an den RestartService', async () => {
    restartService.restart.mockResolvedValue({ restarted: ['documind-ing'] });

    await expect(controller.restart('paperless')).resolves.toEqual({
      restarted: ['documind-ing'],
    });
    expect(restartService.restart).toHaveBeenCalledWith('paperless');
  });
});
