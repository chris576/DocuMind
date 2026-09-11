import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { GatewayClient } from '../src/client.js';

const fetchMock = vi.fn();

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => 'application/json' },
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as unknown as Response;
}

describe('GatewayClient', () => {
  const savedEnv = { ...process.env };

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockReset();
    delete process.env.GATEWAY_URL;
    delete process.env.GATEWAY_API_TOKEN;
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    process.env = { ...savedEnv };
  });

  it('nutzt http://localhost:3001 als Default-Base-URL', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ ok: true }));

    await new GatewayClient().request('/api/test');

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:3001/api/test',
      expect.objectContaining({ method: 'GET' }),
    );
  });

  it('entfernt Trailing-Slashes aus GATEWAY_URL', async () => {
    process.env.GATEWAY_URL = 'http://gateway:9999/';
    fetchMock.mockResolvedValue(jsonResponse({}));

    await new GatewayClient().request('/x');

    expect(fetchMock).toHaveBeenCalledWith(
      'http://gateway:9999/x',
      expect.anything(),
    );
  });

  it('setzt den Bearer-Token nur, wenn GATEWAY_API_TOKEN gesetzt ist', async () => {
    process.env.GATEWAY_API_TOKEN = 'secret';
    fetchMock.mockResolvedValue(jsonResponse({}));
    await new GatewayClient().request('/x');
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe(
      'Bearer secret',
    );

    fetchMock.mockClear();
    delete process.env.GATEWAY_API_TOKEN;
    fetchMock.mockResolvedValue(jsonResponse({}));
    await new GatewayClient().request('/x');
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBeUndefined();
  });

  it('serialisiert POST-Bodies als JSON', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ jobId: '1' }));

    await new GatewayClient().request('/api/ingestion/run', {
      method: 'POST',
      body: { force: true },
    });

    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe('POST');
    expect(init.body).toBe(JSON.stringify({ force: true }));
    expect(init.headers['Content-Type']).toBe('application/json');
  });

  it('sendet GET-Requests ohne Body', async () => {
    fetchMock.mockResolvedValue(jsonResponse({}));

    await new GatewayClient().request('/x');

    expect(fetchMock.mock.calls[0][1].body).toBeUndefined();
  });

  it('wirft bei Fehler-Responses mit Status und Payload', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ message: 'kaputt' }, 502));

    await expect(new GatewayClient().request('/x')).rejects.toThrow(
      'Gateway error 502',
    );
  });

  it('parst Nicht-JSON-Responses als Text', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      headers: { get: () => 'text/plain' },
      text: async () => 'plain text',
    } as unknown as Response);

    await expect(new GatewayClient().request('/x')).resolves.toBe('plain text');
  });
});
