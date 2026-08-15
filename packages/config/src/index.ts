import { z } from 'zod';

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
  
  // Server
  BACKEND_PORT: z.string().default('3001'),
  FRONTEND_PORT: z.string().default('3000'),
  
  // Database
  DATABASE_URL: z.string().default('postgresql://paperless:paperless@localhost:5432/paperless_ai'),
  
  // RabbitMQ
  RABBITMQ_URL: z.string().default('amqp://localhost:5672'),
  
  // JWT
  JWT_SECRET: z.string().min(32),
  
  // Paperless-ngx
  PAPERLESS_API_URL: z.string().url(),
  PAPERLESS_API_TOKEN: z.string(),
  
  // LLM Providers
  OPENAI_API_KEY: z.string().optional(),
  OLLAMA_API_URL: z.string().default('http://localhost:11434'),
  OLLAMA_MODEL: z.string().default('llama3.2'),
  ANTHROPIC_API_KEY: z.string().optional(),
  CUSTOM_BASE_URL: z.string().optional(),
  CUSTOM_API_KEY: z.string().optional(),
  CUSTOM_MODEL: z.string().optional(),
  
  // Vector DB
  VECTOR_DB_TYPE: z.enum(['chroma', 'qdrant', 'pgvector']).default('chroma'),
  CHROMA_URL: z.string().default('http://localhost:8000'),
  QDRANT_URL: z.string().optional(),
  QDRANT_API_KEY: z.string().optional(),
  
  // External API
  EXTERNAL_API_ENABLED: z.string().default('false'),
  EXTERNAL_API_MAX_TOKENS_PER_USER: z.string().default('5'),
  EXTERNAL_API_DEFAULT_MONTHLY_LIMIT: z.string().default('1000'),
  EXTERNAL_API_RATE_LIMIT_RPM: z.string().default('100'),
  
  // RAG Pipelines
  INGESTION_PIPELINE_URL: z.string().default('http://localhost:8001'),
  RETRIEVAL_PIPELINE_URL: z.string().default('http://localhost:8002'),
  GENERATION_PIPELINE_URL: z.string().default('http://localhost:8003'),
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
