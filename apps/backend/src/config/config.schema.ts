import { z } from 'zod';

/**
 * Structured document schema for the Admin-Panel managed configuration.
 *
 * Non-secret values live here; secrets are stored as environment-variable
 * *references* (e.g. `tokenEnv: "PAPERLESS_API_TOKEN"`) and resolved at
 * runtime by the gateway. The document is versioned (`version: 1`) so future
 * migrations can gate on it.
 */

export const connectorSchema = z.object({
  id: z.string().min(1),
  type: z.enum(['paperless', 'docspell']).default('paperless'),
  enabled: z.boolean().default(true),
  url: z.string().optional(),
  tokenEnv: z.string().optional(),
  collection: z.string().optional(),
});

export const llmConfigSchema = z.object({
  provider: z.enum(['openai', 'ollama', 'anthropic', 'custom', 'opencode']).default('ollama'),
  model: z.string().default('llama3.2'),
  baseUrl: z.string().optional(),
  apiKeyEnv: z.string().optional(),
  anthropicApiKeyEnv: z.string().optional(),
  customBaseUrl: z.string().optional(),
  customApiKeyEnv: z.string().optional(),
  customModel: z.string().optional(),
  opencodeBaseUrl: z.string().optional(),
  opencodeUsername: z.string().optional(),
  opencodePasswordEnv: z.string().optional(),
  opencodeModel: z.string().optional(),
});

export const vectorDbConfigSchema = z.object({
  type: z.enum(['chroma', 'qdrant', 'pgvector']).default('chroma'),
  collection: z.string().default('documents'),
  embeddingProvider: z.string().default('sentence_transformer'),
  embeddingModel: z
    .string()
    .default('paraphrase-multilingual-MiniLM-L12-v2'),
  rerankerProvider: z.string().default('cross_encoder'),
  crossEncoderModel: z
    .string()
    .default('cross-encoder/ms-marco-MiniLM-L-6-v2'),
  similarityMetric: z.string().default('cosine'),
  chromaUrl: z.string().optional(),
  qdrantUrl: z.string().optional(),
  qdrantApiKeyEnv: z.string().optional(),
  pgvectorUrl: z.string().optional(),
});

export const hybridSearchConfigSchema = z.object({
  keywordMethod: z.string().default('auto'),
  keywordWeight: z.number().default(0.3),
  semanticWeight: z.number().default(0.7),
  ftsLanguage: z.string().default('german'),
  keywordIndexFile: z.string().default('./data/bm25_index.pkl'),
});

export const retrievalConfigSchema = z.object({
  maxResults: z.number().int().positive().default(20),
});

export const documindConfigSchema = z.object({
  version: z.literal(1).default(1),
  llm: llmConfigSchema.default({}),
  connectors: z.array(connectorSchema).default([]),
  vectorDb: vectorDbConfigSchema.default({}),
  hybridSearch: hybridSearchConfigSchema.default({}),
  retrieval: retrievalConfigSchema.default({}),
});

export type ConnectorConfig = z.infer<typeof connectorSchema>;
export type LlmConfig = z.infer<typeof llmConfigSchema>;
export type VectorDbConfig = z.infer<typeof vectorDbConfigSchema>;
export type HybridSearchConfig = z.infer<typeof hybridSearchConfigSchema>;
export type RetrievalConfig = z.infer<typeof retrievalConfigSchema>;
export type DocuMindConfig = z.infer<typeof documindConfigSchema>;

export function defaultConfig(): DocuMindConfig {
  return documindConfigSchema.parse({});
}
