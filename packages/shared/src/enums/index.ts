export enum LLMProviderType {
  OPENAI = 'openai',
  OLLAMA = 'ollama',
  AZURE = 'azure',
  CUSTOM = 'custom',
  ANTHROPIC = 'anthropic',
}

export enum VectorDBType {
  CHROMA = 'chroma',
  QDRANT = 'qdrant',
  PGVECTOR = 'pgvector',
}

export enum Scope {
  RAG_READ = 'rag:read',
  CHAT_READ = 'chat:read',
  METRICS_READ = 'metrics:read',
  ADMIN = 'admin',
}

export enum ProcessingStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETE = 'complete',
  FAILED = 'failed',
}

export enum QueueName {
  INGESTION = 'ingestion',
  RETRIEVAL = 'retrieval',
  GENERATION = 'generation',
  STATUS = 'status',
}
