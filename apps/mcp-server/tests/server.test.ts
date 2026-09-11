import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

const { requestMock } = vi.hoisted(() => ({
  requestMock: vi.fn<(path: string, options?: unknown) => Promise<unknown>>(),
}));

vi.mock('../src/client.js', () => ({
  GatewayClient: class {
    request = requestMock;
  },
}));

import { server } from '../src/server.js';

type TextContent = Array<{ type: string; text: string }>;

describe('documind MCP-Server', () => {
  let mcpClient: Client;

  beforeAll(async () => {
    const [clientTransport, serverTransport] =
      InMemoryTransport.createLinkedPair();
    mcpClient = new Client({ name: 'test-client', version: '0.0.1' });
    await Promise.all([
      mcpClient.connect(clientTransport),
      server.connect(serverTransport),
    ]);
  });

  beforeEach(() => {
    requestMock.mockReset();
  });

  it('registriert alle sieben Tools', async () => {
    const { tools } = await mcpClient.listTools();
    expect(tools.map((t) => t.name).sort()).toEqual([
      'documind.ask',
      'documind.get_context',
      'documind.ingest',
      'documind.ingest_status',
      'documind.list_collections',
      'documind.pipeline_status',
      'documind.search',
    ]);
  });

  it('documind.ingest startet die Indexierung per POST', async () => {
    const payload = { id: 'job-1', status: 'running' };
    requestMock.mockResolvedValue(payload);

    const result = await mcpClient.callTool({
      name: 'documind.ingest',
      arguments: { namespace: 'paperless', force: true, checkNew: false },
    });

    expect(requestMock).toHaveBeenCalledWith('/api/ingestion/run', {
      method: 'POST',
      body: { namespace: 'paperless', force: true, checkNew: false },
    });
    expect(result.content).toEqual([
      { type: 'text', text: JSON.stringify(payload, null, 2) },
    ]);
  });

  it('documind.ingest_status pollt den Job per GET', async () => {
    requestMock.mockResolvedValue({ id: 'job-1', status: 'completed' });

    await mcpClient.callTool({
      name: 'documind.ingest_status',
      arguments: { jobId: 'job-1' },
    });

    expect(requestMock).toHaveBeenCalledWith('/api/ingestion/jobs/job-1');
  });

  it('documind.search reicht Query, Namespace und Collections durch', async () => {
    requestMock.mockResolvedValue({ results: [] });

    await mcpClient.callTool({
      name: 'documind.search',
      arguments: {
        query: 'Rechnung',
        namespace: 'paperless',
        collections: ['paperless'],
        maxResults: 5,
      },
    });

    expect(requestMock).toHaveBeenCalledWith('/api/retrieval/search', {
      method: 'POST',
      body: {
        query: 'Rechnung',
        namespace: 'paperless',
        collections: ['paperless'],
        maxResults: 5,
      },
    });
  });

  it('documind.get_context baut den Kontext per POST', async () => {
    requestMock.mockResolvedValue({ context: '...' });

    await mcpClient.callTool({
      name: 'documind.get_context',
      arguments: {
        question: 'Was fällig?',
        namespace: 'obs_vault',
        collections: ['obs_vault'],
        maxSources: 3,
      },
    });

    expect(requestMock).toHaveBeenCalledWith('/api/retrieval/context', {
      method: 'POST',
      body: {
        question: 'Was fällig?',
        namespace: 'obs_vault',
        collections: ['obs_vault'],
        maxSources: 3,
      },
    });
  });

  it('documind.ask stellt die Frage per POST', async () => {
    requestMock.mockResolvedValue({ answer: '42' });

    const result = await mcpClient.callTool({
      name: 'documind.ask',
      arguments: { question: 'Antwort?', maxTokens: 100, temperature: 0.2 },
    });

    expect(requestMock).toHaveBeenCalledWith('/api/generation/ask', {
      method: 'POST',
      body: {
        question: 'Antwort?',
        namespace: undefined,
        maxTokens: 100,
        temperature: 0.2,
      },
    });
    expect((result.content as TextContent)[0].text).toContain('42');
  });

  it('documind.pipeline_status fragt den Gateway-Status ab', async () => {
    requestMock.mockResolvedValue([{ namespace: 'paperless' }]);

    await mcpClient.callTool({ name: 'documind.pipeline_status', arguments: {} });

    expect(requestMock).toHaveBeenCalledWith('/api/pipelines/status');
  });

  it('documind.list_collections liest die Collections vom Gateway', async () => {
    requestMock.mockResolvedValue({ collections: ['paperless'] });

    const result = await mcpClient.callTool({
      name: 'documind.list_collections',
      arguments: {},
    });

    expect(requestMock).toHaveBeenCalledWith('/api/config/collections');
    expect((result.content as TextContent)[0].text).toContain('paperless');
  });

  it('meldet Gateway-Fehler als isError-Ergebnis', async () => {
    requestMock.mockRejectedValue(new Error('Gateway error 500: {}'));

    const result = await mcpClient.callTool({
      name: 'documind.pipeline_status',
      arguments: {},
    });

    expect(result.isError).toBe(true);
    expect((result.content as TextContent)[0].text).toContain(
      'Gateway error 500',
    );
  });

  it('validiert Tool-Argumente über die Zod-Schemas', async () => {
    const result = await mcpClient.callTool({
      name: 'documind.ask',
      arguments: { question: 'hi', temperature: 5 },
    });

    expect(result.isError).toBe(true);
    expect(requestMock).not.toHaveBeenCalled();
  });
});
