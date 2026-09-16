import { z } from 'zod';

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
  
  // Server
  BACKEND_PORT: z.string().default('3001'),
  FRONTEND_PORT: z.string().default('3000'),
  
  // Paperless-ngx (backward-compatible; superseded by DOCUMENT_PROVIDER_*)
  PAPERLESS_API_URL: z.string().url(),
  PAPERLESS_API_TOKEN: z.string(),

  // Document source
  DOCUMENT_PROVIDER: z.enum(['paperless', 'docspell']).default('paperless'),
  DOCUMENT_PROVIDER_URL: z.string().optional(),
  DOCUMENT_PROVIDER_TOKEN: z.string().optional(),
  
  // LLM Providers
  OPENAI_API_KEY: z.string().optional(),
  OLLAMA_API_URL: z.string().default('http://localhost:11434'),
  OLLAMA_MODEL: z.string().default('llama3.2'),
  ANTHROPIC_API_KEY: z.string().optional(),
  CUSTOM_BASE_URL: z.string().optional(),
  CUSTOM_API_KEY: z.string().optional(),
  CUSTOM_MODEL: z.string().optional(),
  OPENCODE_BASE_URL: z.string().default('http://127.0.0.1:4096'),
  OPENCODE_USERNAME: z.string().default('opencode'),
  OPENCODE_PASSWORD: z.string().optional(),
  OPENCODE_MODEL: z.string().optional(),
  
  // Vector DB
  VECTOR_DB_TYPE: z.enum(['pgvector']).default('pgvector'),
  PGVECTOR_URL: z.string().optional(),
  
  // External API
  EXTERNAL_API_ENABLED: z.string().default('false'),
  EXTERNAL_API_MAX_TOKENS_PER_USER: z.string().default('5'),
  EXTERNAL_API_DEFAULT_MONTHLY_LIMIT: z.string().default('1000'),
  EXTERNAL_API_RATE_LIMIT_RPM: z.string().default('100'),
  
  // RAG Pipelines
  INGESTION_PIPELINE_URL: z.string().default('http://localhost:8001'),
  RETRIEVAL_PIPELINE_URL: z.string().default('http://localhost:8002'),
  GENERATION_PIPELINE_URL: z.string().default('http://localhost:8003'),

  // Gateway / MCP
  GATEWAY_API_TOKEN: z.string().optional(),
  PIPELINE_REGISTRY_JSON: z.string().optional(),

  // Pipeline-Ports (Container/Netzwerk + Host/publiziert)
  INGESTION_PORT: z.string().default('8001'),
  RETRIEVAL_PORT: z.string().default('8002'),
  GENERATION_PORT: z.string().default('8003'),
  INGESTION_HOST_PORT: z.string().default('8001'),
  RETRIEVAL_HOST_PORT: z.string().default('8002'),
  GENERATION_HOST_PORT: z.string().default('8003'),
});

export type Env = z.infer<typeof envSchema>;

export function validateEnv(): Env {
  const result = envSchema.safeParse(process.env);
  
  if (!result.success) {
    console.error('Environment validation failed:');
    console.error(result.error.format());
    throw new Error('Invalid environment configuration');
  }
  
  return result.data;
}

export const env = validateEnv();
