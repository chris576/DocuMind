import { Module } from '@nestjs/common';
import { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import { mkdtempSync, rmSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';

import { AppConfigModule } from '../src/config/app-config.module';
import { PipelinesModule } from '../src/pipelines/pipelines.module';

// Isolierter CONFIG_FILE-Pfad, damit die Tests nie die echte config.json anfassen.
const TMP_DIR = mkdtempSync(join(tmpdir(), 'documind-gateway-config-'));
process.env.CONFIG_FILE = join(TMP_DIR, 'config.json');

@Module({
  imports: [AppConfigModule, PipelinesModule],
})
class GatewayConfigTestModule {}

describe('Gateway Config & Pipelines (Integration)', () => {
  let app: INestApplication;

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({
      imports: [GatewayConfigTestModule],
    }).compile();

    app = moduleRef.createNestApplication();
    app.setGlobalPrefix('api');
    await app.init();
  });

  afterAll(async () => {
    await app?.close();
    rmSync(TMP_DIR, { recursive: true, force: true });
  });

  it('liefert die Default-Konfiguration (GET /api/config)', async () => {
    const res = await request(app.getHttpServer()).get('/api/config').expect(200);

    expect(res.body.version).toBe(1);
    expect(res.body.llm.provider).toBe('ollama');
    expect(res.body.vectorDb.collection).toBe('documents');
  });

  it('speichert und liest Konfiguration (PUT /api/config)', async () => {
    await request(app.getHttpServer())
      .put('/api/config')
      .send({ llm: { provider: 'openai', model: 'gpt-4' } })
      .expect(200);

    const res = await request(app.getHttpServer()).get('/api/config').expect(200);
    expect(res.body.llm.provider).toBe('openai');
    expect(res.body.llm.model).toBe('gpt-4');
  });

  it('liefert die Collection-Liste (GET /api/config/collections)', async () => {
    await request(app.getHttpServer())
      .put('/api/config')
      .send({
        connectors: [
          { id: 'paperless', type: 'paperless', enabled: true },
          { id: 'obsidian', type: 'docspell', enabled: true, collection: 'obs_vault' },
        ],
      })
      .expect(200);

    const res = await request(app.getHttpServer())
      .get('/api/config/collections')
      .expect(200);
    expect(res.body.collections).toEqual(['paperless', 'obs_vault']);
  });

  it('liefert den collections-Slice (GET /api/config/slice/collections)', async () => {
    const res = await request(app.getHttpServer())
      .get('/api/config/slice/collections')
      .expect(200);

    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body).toContain('paperless');
  });

  it('liefert die Pipeline-Registry (GET /api/pipelines)', async () => {
    const res = await request(app.getHttpServer()).get('/api/pipelines').expect(200);

    expect(res.body.namespaces).toContain('paperless');
    expect(Array.isArray(res.body.pipelines)).toBe(true);
  });

  it('lehnt Restart ohne Container-Mapping ab (501)', async () => {
    const res = await request(app.getHttpServer())
      .post('/api/pipelines/paperless/restart')
      .expect(501);

    expect(res.body.message).toContain('PIPELINE_CONTAINER_MAP');
  });

  it('lehnt ungültige Konfigurationen ab (400)', async () => {
    const res = await request(app.getHttpServer())
      .put('/api/config')
      .send({ vectorDb: { type: 'mysql' } })
      .expect(400);

    expect(res.body.message).toContain('Invalid config');
  });

  it('liefert den llm-Slice (GET /api/config/slice/llm)', async () => {
    const res = await request(app.getHttpServer())
      .get('/api/config/slice/llm')
      .expect(200);

    expect(res.body).toHaveProperty('provider');
    expect(res.body).toHaveProperty('model');
  });

  it('gibt 404 für unbekannte Slices zurück', async () => {
    const res = await request(app.getHttpServer())
      .get('/api/config/slice/unknown')
      .expect(404);

    expect(res.body.message).toContain('Unknown config slice');
  });

  it('maskiert Credentials in Connector-URLs beim Lesen', async () => {
    await request(app.getHttpServer())
      .put('/api/config')
      .send({
        connectors: [
          {
            id: 'paperless',
            type: 'paperless',
            enabled: true,
            url: 'http://user:geheim@paperless:8000',
          },
        ],
      })
      .expect(200);

    const res = await request(app.getHttpServer())
      .get('/api/config')
      .expect(200);

    const connector = res.body.connectors.find(
      (c: { id: string }) => c.id === 'paperless',
    );
    expect(connector.url).toBe('http://user:***@paperless:8000');
    expect(connector.url).not.toContain('geheim');
  });
});
