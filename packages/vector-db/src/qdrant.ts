import { QdrantClient } from '@qdrant/js-client-rest';
import { IVectorDB, VectorDBConfig, VectorDBDocument, VectorDBSearchResult } from './types';

export class QdrantVectorDB implements IVectorDB {
  private client: QdrantClient | null = null;
  private collectionName: string;
  private ready = false;

  constructor(private config: VectorDBConfig) {
    this.collectionName = config.collection || 'documents';
  }

  async initialize(): Promise<boolean> {
    try {
      this.client = new QdrantClient({ url: this.config.url, apiKey: this.config.apiKey });
      const collections = await this.client.getCollections();
      const exists = collections.collections.some((c) => c.name === this.collectionName);

      if (!exists) {
        await this.client.createCollection(this.collectionName, {
          vectors: {
            size: this.config.embeddingDimension || 384,
            distance: 'Cosine',
          },
        });
      }

      this.ready = true;
      return true;
    } catch (error) {
      this.ready = false;
      throw error;
    }
  }

  async addDocuments(documents: VectorDBDocument[]): Promise<void> {
    if (!this.client) throw new Error('Qdrant not initialized');
    // Note: Requires external embedding generation before upsert
    const points = documents.map((d, i) => ({
      id: d.id,
      vector: [], // Placeholder - must be filled by embedding model
      payload: { title: d.title, content: d.content, ...d.metadata },
    }));

    await this.client.upsert(this.collectionName, { points });
  }

  async search(query: string, topK = 10): Promise<VectorDBSearchResult[]> {
    if (!this.client) throw new Error('Qdrant not initialized');
    // Note: Requires query embedding from external model
    const results = await this.client.query(this.collectionName, {
      query: [] as number[], // Placeholder
      limit: topK,
    });

    return results.points.map((r: any) => ({
      id: String(r.id),
      title: (r.payload?.title as string) || '',
      content: (r.payload?.content as string) || '',
      score: r.score,
      metadata: (r.payload as Record<string, any>) || {},
    }));
  }

  async deleteCollection(): Promise<void> {
    if (!this.client) throw new Error('Qdrant not initialized');
    await this.client.deleteCollection(this.collectionName);
    this.ready = false;
  }

  async getStatus(): Promise<{ ready: boolean; documentCount: number }> {
    if (!this.client || !this.ready) return { ready: false, documentCount: 0 };
    try {
      const info = await this.client.getCollection(this.collectionName);
      return { ready: true, documentCount: info.points_count || 0 };
    } catch {
      return { ready: false, documentCount: 0 };
    }
  }
}
