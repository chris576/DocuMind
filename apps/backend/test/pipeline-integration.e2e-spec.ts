import { Module } from '@nestjs/common';
import { INestApplication } from '@nestjs/common';
import { JwtModule, JwtService } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';

import { JwtStrategy } from '../src/auth/jwt.strategy';
import { ChatModule } from '../src/chat/chat.module';
import { RagModule } from '../src/rag/rag.module';

// Env VOR der Modul-Konstruktion setzen: RagService/ChatService lesen die
// Pipeline-URLs und AuthModule/JwtStrategy lesen JWT_SECRET im Konstruktor.
process.env.JWT_SECRET = process.env.JWT_SECRET || 'integration-test-secret';
process.env.INGESTION_PIPELINE_URL = 'http://127.0.0.1:8001';
process.env.RETRIEVAL_PIPELINE_URL = 'http://127.0.0.1:8002';
process.env.GENERATION_PIPELINE_URL = 'http://127.0.0.1:8003';

// DB-freies Test-Modul: nur Rag/Chat (HTTP-Proxy) + JWT-Auth. DocumentsModule
// (TypeORM) bleibt außen vor, damit kein Postgres benötigt wird.
@Module({
  imports: [
    PassportModule.register({ defaultStrategy: 'jwt' }),
    JwtModule.register({
      secret: process.env.JWT_SECRET,
      signOptions: { expiresIn: '1h' },
    }),
    RagModule,
    ChatModule,
  ],
  providers: [JwtStrategy],
})
class IntegrationTestModule {}

describe('Backend ↔ Pipelines (Integration)', () => {
  let app: INestApplication;
  let token: string;

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({
      imports: [IntegrationTestModule],
    }).compile();

    app = moduleRef.createNestApplication();
    await app.init();

    const jwtService = moduleRef.get(JwtService);
    token = jwtService.sign({ sub: 1, username: 'integration', scopes: [] });
  });

  afterAll(async () => {
    await app?.close();
  });

  it('löst die Indexierung über die Ingestion-Pipeline aus', async () => {
    const res = await request(app.getHttpServer())
      .post('/rag/index')
      .set('Authorization', `Bearer ${token}`)
      .expect(201);

    expect(res.body.status).toBe('started');
  });

  it('liefert den Indexierungs-Status der Ingestion-Pipeline', async () => {
    const res = await request(app.getHttpServer())
      .get('/rag/index/status')
      .set('Authorization', `Bearer ${token}`)
      .expect(200);

    expect(res.body.service).toBe('ingestion-pipeline');
    expect(res.body.initialized).toBe(true);
  });

  it('sucht über die Retrieval-Pipeline', async () => {
    const res = await request(app.getHttpServer())
      .post('/rag/search')
      .set('Authorization', `Bearer ${token}`)
      .send({ query: 'invoice' })
      .expect(201);

    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body[0].title).toBe('Rechnung 2024-001');
    expect(res.body[0].doc_id).toBe(1);
  });

  it('beantwortet eine Frage über Retrieval→Generation (RAG-Kette)', async () => {
    const res = await request(app.getHttpServer())
      .post('/rag/ask')
      .set('Authorization', `Bearer ${token}`)
      .send({ question: 'Wann ist die Rechnung fällig?', maxSources: 2 })
      .expect(201);

    expect(res.body.answer).toContain('Antwort');
    expect(res.body.sources).toHaveLength(2);
    expect(res.body.sources[0].title).toBe('Rechnung 2024-001');
    expect(res.body.sources[1].title).toBe('Vertrag Muster');
    // metrics wird aus den Token-Feldern des Generation-Responses gemappt.
    expect(res.body.metrics).toEqual({
      promptTokens: 10,
      completionTokens: 5,
      totalTokens: 15,
    });
  });

  it('aggregiert den Status von Retrieval- und Generation-Pipeline', async () => {
    const res = await request(app.getHttpServer())
      .get('/rag/status')
      .set('Authorization', `Bearer ${token}`)
      .expect(200);

    expect(res.body.retrieval.initialized).toBe(true);
    expect(res.body.generation.status).toBe('ok');
  });

  it('initialisiert einen Dokument-Chat über die Generation-Pipeline', async () => {
    const res = await request(app.getHttpServer())
      .post('/chat/init')
      .set('Authorization', `Bearer ${token}`)
      .send({ documentId: 1 })
      .expect(201);

    expect(res.body.status).toBe('initialized');
    expect(res.body.chat_id).toBeTruthy();
  });
});
