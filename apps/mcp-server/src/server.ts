#!/usr/bin/env node
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { GatewayClient } from './client.js';

const client = new GatewayClient();

const server = new McpServer({
  name: 'documind',
  version: '1.0.0',
});

function textResult(value: unknown) {
  return {
    content: [
      { type: 'text' as const, text: JSON.stringify(value, null, 2) },
    ],
  };
}

server.registerTool(
  'documind.ingest',
  {
    description:
      'Start document indexing in the background for a namespace (document source, e.g. paperless). Returns a job id to poll via documind.ingest_status.',
    inputSchema: {
      namespace: z.string().optional(),
      force: z.boolean().optional(),
      checkNew: z.boolean().optional(),
    },
  },
  async (args) => {
    const job = await client.request('/api/ingestion/run', {
      method: 'POST',
      body: {
        namespace: args.namespace,
        force: args.force,
        checkNew: args.checkNew,
      },
    });
    return textResult(job);
  },
);

server.registerTool(
  'documind.ingest_status',
  {
    description: 'Poll the status of a background ingestion job by id.',
    inputSchema: {
      jobId: z.string(),
    },
  },
  async (args) => {
    const job = await client.request(`/api/ingestion/jobs/${args.jobId}`);
    return textResult(job);
  },
);

server.registerTool(
  'documind.search',
  {
    description:
      'Semantic/hybrid search over the document archive for a namespace.',
    inputSchema: {
      query: z.string(),
      namespace: z.string().optional(),
      maxResults: z.number().int().positive().optional(),
    },
  },
  async (args) => {
    const results = await client.request('/api/retrieval/search', {
      method: 'POST',
      body: {
        query: args.query,
        namespace: args.namespace,
        maxResults: args.maxResults,
      },
    });
    return textResult(results);
  },
);

server.registerTool(
  'documind.get_context',
  {
    description:
      'Build retrieval context (sources + snippets) for a question within a namespace.',
    inputSchema: {
      question: z.string(),
      namespace: z.string().optional(),
      maxSources: z.number().int().positive().optional(),
    },
  },
  async (args) => {
    const context = await client.request('/api/retrieval/context', {
      method: 'POST',
      body: {
        question: args.question,
        namespace: args.namespace,
        maxSources: args.maxSources,
      },
    });
    return textResult(context);
  },
);

server.registerTool(
  'documind.ask',
  {
    description:
      'Ask a natural-language question over the document archive. Returns the full answer text (no token streaming in v1).',
    inputSchema: {
      question: z.string(),
      namespace: z.string().optional(),
      maxTokens: z.number().int().positive().optional(),
      temperature: z.number().min(0).max(2).optional(),
    },
  },
  async (args) => {
    const answer = await client.request('/api/generation/ask', {
      method: 'POST',
      body: {
        question: args.question,
        namespace: args.namespace,
        maxTokens: args.maxTokens,
        temperature: args.temperature,
      },
    });
    return textResult(answer);
  },
);

server.registerTool(
  'documind.pipeline_status',
  {
    description:
      'Report the status of all pipelines and namespaces known to the gateway.',
    inputSchema: {},
  },
  async () => {
    const status = await client.request('/api/pipelines/status');
    return textResult(status);
  },
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((error) => {
  console.error('documind-mcp-server failed:', error);
  process.exit(1);
});
