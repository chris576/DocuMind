import { Client } from 'pg';
import { IVectorDB, VectorDBConfig, VectorDBDocument, VectorDBSearchResult } from './types';

export class PgVectorVectorDB implements IVectorDB {
  private client: Client | null = null;
  private tableName: string;
  private ready = false;

  constructor(private config: VectorDBConfig) {
    this.tableName = config.collection || 'documents';
  }

  async initialize(): Promise<boolean> {
    try {
      this.client = new Client({ connectionString: this.config.url });
      await this.client.connect();
      await this.client.query('CREATE EXTENSION IF NOT EXISTS vector');
      await this.client.query(`
        CREATE TABLE IF NOT EXISTS ${this.tableName} (
          id TEXT PRIMARY KEY,
          title TEXT NOT NULL,
          content TEXT NOT NULL,
          embedding VECTOR(${this.config.embeddingDimension || 384}),
          metadata JSONB DEFAULT '{}'
        )
      `);

      this.ready = true;
      return true;
    } catch (error) {
      this.ready = false;
      throw error;
    }
  }

  async addDocuments(documents: VectorDBDocument[]): Promise<void> {
    if (!this.client) throw new Error('PGVector not initialized');
    // Placeholder: embedding vector must be provided externally
    for (const doc of documents) {
      await this.client.query(
        `INSERT INTO ${this.tableName} (id, title, content, embedding, metadata)
         VALUES ($1, $2, $3, $4, $5)
         ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title, content = EXCLUDED.content, metadata = EXCLUDED.metadata`,
        [doc.id, doc.title, doc.content, JSON.stringify([]), JSON.stringify(doc.metadata || {})],
      );
    }
  }

  async search(query: string, topK = 10): Promise<VectorDBSearchResult[]> {
    if (!this.client) throw new Error('PGVector not initialized');
    // Placeholder: requires external query embedding
    const result = await this.client.query(
      `SELECT id, title, content, metadata, 1 - (embedding <=> $1::vector) AS score
       FROM ${this.tableName}
       ORDER BY embedding <=> $1::vector
       LIMIT $2`,
      [JSON.stringify([]), topK],
    );

    return result.rows.map((row) => ({
      id: row.id,
      title: row.title,
      content: row.content,
      score: parseFloat(row.score) || 0,
      metadata: row.metadata || {},
    }));
  }

  async deleteCollection(): Promise<void> {
    if (!this.client) throw new Error('PGVector not initialized');
    await this.client.query(`DROP TABLE IF EXISTS ${this.tableName}`);
    this.ready = false;
  }

  async getStatus(): Promise<{ ready: boolean; documentCount: number }> {
    if (!this.client || !this.ready) return { ready: false, documentCount: 0 };
    try {
      const result = await this.client.query(`SELECT COUNT(*) FROM ${this.tableName}`);
      return { ready: true, documentCount: parseInt(result.rows[0].count, 10) };
    } catch {
      return { ready: false, documentCount: 0 };
    }
  }
}
