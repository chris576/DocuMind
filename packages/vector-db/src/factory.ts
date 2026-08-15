import { IVectorDB, VectorDBConfig } from './types';
import { ChromaVectorDB } from './chroma';
import { QdrantVectorDB } from './qdrant';
import { PgVectorVectorDB } from './pgvector';

export class VectorDBFactory {
  static create(config: VectorDBConfig): IVectorDB {
    switch (config.type) {
      case 'chroma':
        return new ChromaVectorDB(config);
      case 'qdrant':
        return new QdrantVectorDB(config);
      case 'pgvector':
        return new PgVectorVectorDB(config);
      default:
        throw new Error(`Unsupported vector database type: ${config.type}`);
    }
  }
}

export * from './types';
export { ChromaVectorDB, QdrantVectorDB, PgVectorVectorDB };
