import { Module } from '@nestjs/common';
import { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';

import { IngestionModule } from '../src/ingestion/ingestion.module';
import { RetrievalModule } from '../src/retrieval/retrieval.module';
import { GenerationModule } from '../src/generation/generation.module';
import { HealthModule } from '../src/health/health.module';

// Env VOR der Modul-Konstruktion setzen: die Services lesen die
// Pipeline-URLs im Konstruktor.
process.env.INGESTION_PIPELINE_URL = 'http://127.0.0.1:8001';
process.env.RETRIEVAL_PIPELINE_URL = 'http://127.0.0.1:8002';
process.env.GENERATION_PIPELINE_URL = 'http://127.0.0.1:8003';

// DB-freies Test-Modul: nur die drei HTTP-Proxy-Module (keine Auth, kein Postgres).
@Module({
  imports: [IngestionModule, RetrievalModule, GenerationModule, HealthModule],
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

    expect(res.body.id).toBeTruthy();
    expect(res.body.status).toBe('running');
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

  it('löst die synchrone Indexierung über die Ingestion-Pipeline aus', async () => {
    const res = await request(app.getHttpServer())
      .post('/api/ingestion/run/sync')
      .send({ force: true, checkNew: false })
      .expect(201);

    expect(res.body.status).toBe('completed');
    expect(res.body.processed).toBe(2);
  });

  it('liefert den Retrieval-Kontext für eine Frage', async () => {
    const res = await request(app.getHttpServer())
      .post('/api/retrieval/context')
      .send({ question: 'Rechnung', maxSources: 2 })
      .expect(201);

    expect(res.body.query).toBe('Rechnung');
    expect(res.body.context).toContain('Rechnung 2024-001');
    expect(Array.isArray(res.body.sources)).toBe(true);
  });

  it('liefert den Status der Retrieval-Pipeline', async () => {
    const res = await request(app.getHttpServer())
      .get('/api/retrieval/status')
      .expect(200);

    expect(res.body.initialized).toBe(true);
  });

  it('liefert den eigenen Health-Status des Backends', async () => {
    const res = await request(app.getHttpServer())
      .get('/api/health')
      .expect(200);

    expect(res.body.status).toBe('ok');
    expect(res.body.service).toBe('dms-rag-backend');
  });

  it('streamt die Antwort über SSE (ask/stream)', async () => {
    const res = await request(app.getHttpServer())
      .post('/api/generation/ask/stream')
      .send({ question: 'Wann ist die Rechnung fällig?' })
      .expect(201)
      .expect('Content-Type', /text\/event-stream/);

    expect(res.text).toContain('data: ');
    expect(res.text).toContain('[DONE]');
  });

  it('sendet eine Chat-Nachricht über die Generation-Pipeline', async () => {
    const init = await request(app.getHttpServer())
      .post('/api/generation/chat/init')
      .send({ documentId: 1 })
      .expect(201);
    const chatId = init.body.chat_id;

    const res = await request(app.getHttpServer())
      .post('/api/generation/chat/message')
      .send({ chatId, message: 'Hallo' })
      .expect(201);

    expect(res.body.chat_id).toBe(chatId);
    expect(res.body.role).toBe('assistant');
    expect(res.body.message).toBeTruthy();
  });

  it('streamt eine Chat-Antwort über SSE (chat/message/stream)', async () => {
    const init = await request(app.getHttpServer())
      .post('/api/generation/chat/init')
      .send({ documentId: 1 })
      .expect(201);
    const chatId = init.body.chat_id;

    const res = await request(app.getHttpServer())
      .post('/api/generation/chat/message/stream')
      .send({ chatId, message: 'Hallo' })
      .expect(201)
      .expect('Content-Type', /text\/event-stream/);

    expect(res.text).toContain('[DONE]');
  });
});
