import { Module } from '@nestjs/common';
import { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';

import { IngestionModule } from '../src/ingestion/ingestion.module';
import { RetrievalModule } from '../src/retrieval/retrieval.module';
import { GenerationModule } from '../src/generation/generation.module';

// Env VOR der Modul-Konstruktion setzen: die Services lesen die
// Pipeline-URLs im Konstruktor.
process.env.INGESTION_PIPELINE_URL = 'http://127.0.0.1:8001';
process.env.RETRIEVAL_PIPELINE_URL = 'http://127.0.0.1:8002';
process.env.GENERATION_PIPELINE_URL = 'http://127.0.0.1:8003';

// DB-freies Test-Modul: nur die drei HTTP-Proxy-Module (keine Auth, kein Postgres).
@Module({
  imports: [IngestionModule, RetrievalModule, GenerationModule],
})
class IntegrationTestModule {}

describe('Backend ↔ Pipelines (Integration)', () => {
  let app: INestApplication;

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({
      imports: [IntegrationTestModule],
    }).compile();

    app = moduleRef.createNestApplication();
    app.setGlobalPrefix('api');
    await app.init();
  });

  afterAll(async () => {
    await app?.close();
  });

  it('löst die Indexierung über die Ingestion-Pipeline aus', async () => {
    const res = await request(app.getHttpServer())
      .post('/api/ingestion/run')
      .send({ force: false, checkNew: true })
      .expect(201);

    expect(res.body.status).toBe('started');
  });

  it('liefert den Indexierungs-Status der Ingestion-Pipeline', async () => {
    const res = await request(app.getHttpServer())
      .get('/api/ingestion/status')
      .expect(200);

    expect(res.body.service).toBe('ingestion-pipeline');
    expect(res.body.initialized).toBe(true);
  });

  it('sucht über die Retrieval-Pipeline', async () => {
    const res = await request(app.getHttpServer())
      .post('/api/retrieval/search')
      .send({ query: 'invoice' })
      .expect(201);

    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body[0].title).toBe('Rechnung 2024-001');
    expect(res.body[0].docId).toBe(1);
  });

  it('beantwortet eine Frage über die Generation-Pipeline', async () => {
    const res = await request(app.getHttpServer())
      .post('/api/generation/ask')
      .send({ question: 'Wann ist die Rechnung fällig?' })
      .expect(201);

    expect(res.body.answer).toContain('Antwort');
    // metrics wird aus den Token-Feldern des Generation-Responses gemappt.
    expect(res.body.metrics).toEqual({
      promptTokens: 10,
      completionTokens: 5,
      totalTokens: 15,
    });
  });

  it('liefert den Status der Generation-Pipeline', async () => {
    const res = await request(app.getHttpServer())
      .get('/api/generation/status')
      .expect(200);

    expect(res.body.status).toBe('ok');
  });

  it('initialisiert einen Dokument-Chat über die Generation-Pipeline', async () => {
    const res = await request(app.getHttpServer())
      .post('/api/generation/chat/init')
      .send({ documentId: 1 })
      .expect(201);

    expect(res.body.status).toBe('initialized');
    expect(res.body.chat_id).toBeTruthy();
  });
});
