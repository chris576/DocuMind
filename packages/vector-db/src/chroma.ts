import { ChromaClient, DefaultEmbeddingFunction } from 'chromadb';
import { IVectorDB, VectorDBConfig, VectorDBDocument, VectorDBSearchResult } from './types';

export class ChromaVectorDB implements IVectorDB {
  private client: ChromaClient | null = null;
  private collectionName: string;
  private ready = false;
  private embeddingFunction = new DefaultEmbeddingFunction();

  constructor(private config: VectorDBConfig) {
    this.collectionName = config.collection || 'documents';
  }

  async initialize(): Promise<boolean> {
    try {
      this.client = new ChromaClient({ path: this.config.url });
      const collections = await this.client.listCollections();
      const exists = collections.some((c: any) => c.name === this.collectionName);

      if (!exists) {
        await this.client.createCollection({
          name: this.collectionName,
          embeddingFunction: this.embeddingFunction,
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
    if (!this.client) throw new Error('ChromaDB not initialized');

    const collection = await this.client.getCollection({
      name: this.collectionName,
      embeddingFunction: this.embeddingFunction,
    });
    const ids = documents.map((d) => d.id);
    const texts = documents.map((d) => `${d.title} ${d.content}`);
    const metadatas = documents.map((d) => ({
      title: d.title,
      ...d.metadata,
    }));

    await collection.add({ ids, documents: texts, metadatas });
  }

  async search(query: string, topK = 10): Promise<VectorDBSearchResult[]> {
    if (!this.client) throw new Error('ChromaDB not initialized');

    const collection = await this.client.getCollection({
      name: this.collectionName,
      embeddingFunction: this.embeddingFunction,
    });
    const results = await collection.query({ queryTexts: [query], nResults: topK });

    if (!results.ids?.[0]?.length) return [];

    return results.ids[0].map((id, i) => ({
      id: String(id),
      title: String(results.metadatas?.[0]?.[i]?.title || ''),
      content: String(results.documents?.[0]?.[i] || ''),
      score: Number(results.distances?.[0]?.[i] ?? 0),
      metadata: (results.metadatas?.[0]?.[i] as Record<string, any>) || {},
    }));
  }

  async deleteCollection(): Promise<void> {
    if (!this.client) throw new Error('ChromaDB not initialized');
    await this.client.deleteCollection({ name: this.collectionName });
    this.ready = false;
  }

  async getStatus(): Promise<{ ready: boolean; documentCount: number }> {
    if (!this.client || !this.ready) return { ready: false, documentCount: 0 };
    try {
      const collection = await this.client.getCollection({
        name: this.collectionName,
        embeddingFunction: this.embeddingFunction,
      });
      const count = await collection.count();
      return { ready: true, documentCount: count };
    } catch {
      return { ready: false, documentCount: 0 };
    }
  }
}
