export interface VectorDBDocument {
  id: string;
  title: string;
  content: string;
  metadata?: Record<string, any>;
}

export interface VectorDBSearchResult {
  id: string;
  title: string;
  content: string;
  score: number;
  metadata?: Record<string, any>;
}

export interface VectorDBConfig {
  type: 'chroma' | 'qdrant' | 'pgvector';
  url: string;
  collection?: string;
  apiKey?: string;
  embeddingDimension?: number;
}

export interface IVectorDB {
  initialize(): Promise<boolean>;
  addDocuments(documents: VectorDBDocument[]): Promise<void>;
  search(query: string, topK?: number): Promise<VectorDBSearchResult[]>;
  deleteCollection(): Promise<void>;
  getStatus(): Promise<{ ready: boolean; documentCount: number }>;
}
