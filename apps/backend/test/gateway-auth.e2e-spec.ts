import { INestApplication, Module } from '@nestjs/common';
import { APP_GUARD } from '@nestjs/core';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { GatewayAuthGuard } from '../src/auth/gateway-auth.guard';
import { HealthModule } from '../src/health/health.module';
import { IngestionModule } from '../src/ingestion/ingestion.module';

@Module({
  imports: [HealthModule, IngestionModule],
  providers: [{ provide: APP_GUARD, useClass: GatewayAuthGuard }],
})
class AuthTestModule {}

async function createApp(): Promise<INestApplication> {
  const moduleRef = await Test.createTestingModule({
    imports: [AuthTestModule],
  }).compile();
  const app = moduleRef.createNestApplication();
  app.setGlobalPrefix('api');
  await app.init();
  return app;
}

describe('Gateway Auth Guard (E2E)', () => {
  describe('mit gesetztem GATEWAY_API_TOKEN', () => {
    let app: INestApplication;

    beforeAll(async () => {
      process.env.GATEWAY_API_TOKEN = 'e2e-secret-token';
      app = await createApp();
    });

    afterAll(async () => {
      await app?.close();
      delete process.env.GATEWAY_API_TOKEN;
    });

    it('weist Requests ohne Token ab (403)', async () => {
      await request(app.getHttpServer()).get('/api/ingestion/jobs').expect(403);
    });

    it('weist Requests mit falschem Token ab (403)', async () => {
      await request(app.getHttpServer())
        .get('/api/ingestion/jobs')
        .set('Authorization', 'Bearer falsch')
        .expect(403);
    });

    it('lässt Requests mit gültigem Token durch', async () => {
      const res = await request(app.getHttpServer())
        .get('/api/ingestion/jobs')
        .set('Authorization', 'Bearer e2e-secret-token')
        .expect(200);

      expect(Array.isArray(res.body)).toBe(true);
    });

    it('lässt /api/health ohne Token durch', async () => {
      const res = await request(app.getHttpServer())
        .get('/api/health')
        .expect(200);

      expect(res.body.status).toBe('ok');
    });

    it('lässt Pfade außerhalb von /api ohne Token durch (kein 403)', async () => {
      const res = await request(app.getHttpServer()).get('/api-docs');

      expect(res.status).not.toBe(403);
    });
  });

  describe('ohne GATEWAY_API_TOKEN (Guard deaktiviert)', () => {
    let app: INestApplication;

    beforeAll(async () => {
      delete process.env.GATEWAY_API_TOKEN;
      app = await createApp();
    });

    afterAll(async () => {
      await app?.close();
    });

    it('lässt Requests ohne Token durch (Dev-Modus)', async () => {
      await request(app.getHttpServer()).get('/api/ingestion/jobs').expect(200);
    });
  });
});
