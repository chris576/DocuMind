export enum LLMProviderType {
  OPENAI = 'openai',
  OLLAMA = 'ollama',
  AZURE = 'azure',
  CUSTOM = 'custom',
  ANTHROPIC = 'anthropic',
  OPENCODE = 'opencode',
}

export enum VectorDBType {
  CHROMA = 'chroma',
  QDRANT = 'qdrant',
  PGVECTOR = 'pgvector',
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
