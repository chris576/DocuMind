import { HttpException, HttpStatus, Injectable } from '@nestjs/common';
import * as fs from 'fs';
import * as path from 'path';
import {
  DocuMindConfig,
  documindConfigSchema,
  defaultConfig,
} from './config.schema';

/**
 * Owns the Admin-Panel configuration document (JSON file on the gateway).
 *
 * - GET returns the document with any embedded URL credentials redacted.
 * - Slices (`/api/config/slice/:name`) resolve secret env references so the
 *   Python pipelines can consume a flat, snake_case config with env fallback.
 * - PUT validates the full document and writes it atomically.
 */
@Injectable()
export class AppConfigService {
  private readonly filePath: string;
  private config: DocuMindConfig;

  constructor() {
    this.filePath = path.resolve(
      process.env.CONFIG_FILE || './config/config.json',
    );
    this.config = this.load();
  }

  getConfig(): DocuMindConfig {
    return this.redactSecrets(this.config);
  }

  getCollections(): string[] {
    return this.connectorsSlice(this.config).map((c) => c.collection as string);
  }

  getSlice(name: string): unknown {
    switch (name) {
      case 'llm':
        return this.llmSlice(this.config);
      case 'dms':
        return this.dmsSlice(this.config);
      case 'connectors':
        return this.connectorsSlice(this.config);
      case 'collections':
        return this.getCollections();
      case 'vector-db':
        return this.vectorDbSlice(this.config);
      case 'retrieval':
        return { max_results: this.config.retrieval.maxResults };
      default:
        throw new HttpException(
          `Unknown config slice: ${name}`,
          HttpStatus.NOT_FOUND,
        );
    }
  }

  saveConfig(input: unknown): DocuMindConfig {
    const restored = this.restoreUrlSecrets(input);
    const parsed = documindConfigSchema.parse(restored);
    this.write(parsed);
    this.config = parsed;
    return this.redactSecrets(parsed);
  }

  private load(): DocuMindConfig {
    try {
      const raw = fs.readFileSync(this.filePath, 'utf-8');
      return documindConfigSchema.parse(JSON.parse(raw));
    } catch {
      return defaultConfig();
    }
  }

  private write(config: DocuMindConfig): void {
    fs.mkdirSync(path.dirname(this.filePath), { recursive: true });
    const tmp = `${this.filePath}.tmp`;
    fs.writeFileSync(tmp, JSON.stringify(config, null, 2), 'utf-8');
    fs.renameSync(tmp, this.filePath);
  }

  private resolveEnv(name?: string): string | undefined {
    return name ? process.env[name] : undefined;
  }

  private llmSlice(c: DocuMindConfig): Record<string, unknown> {
    return {
      provider: c.llm.provider,
      model: c.llm.model,
      api_key: this.resolveEnv(c.llm.apiKeyEnv),
      base_url: c.llm.baseUrl ?? process.env.OLLAMA_BASE_URL,
      anthropic_api_key: this.resolveEnv(c.llm.anthropicApiKeyEnv),
      custom_base_url: c.llm.customBaseUrl,
      custom_api_key: this.resolveEnv(c.llm.customApiKeyEnv),
      custom_model: c.llm.customModel,
      opencode_base_url: c.llm.opencodeBaseUrl,
      opencode_username: c.llm.opencodeUsername,
      opencode_password: this.resolveEnv(c.llm.opencodePasswordEnv),
      opencode_model: c.llm.opencodeModel,
    };
  }

  private dmsSlice(c: DocuMindConfig): Record<string, unknown> {
    const connector = c.connectors.find((x) => x.enabled) ?? c.connectors[0];
    return {
      document_provider: connector?.type ?? 'paperless',
      document_provider_url:
        connector?.url ?? process.env.PAPERLESS_API_URL ?? undefined,
      document_provider_token:
        this.resolveEnv(connector?.tokenEnv) ?? process.env.PAPERLESS_API_TOKEN,
    };
  }

  private connectorsSlice(c: DocuMindConfig): Record<string, unknown>[] {
    const enabled = c.connectors.filter((x) => x.enabled);
    const connectors = enabled.length > 0 ? enabled : c.connectors;

    if (connectors.length === 0) {
      // Env fallback: a single Paperless connector.
      return [
        {
          id: 'paperless',
          type: 'paperless',
          enabled: true,
          url:
            process.env.PAPERLESS_API_URL ?? process.env.DOCUMENT_PROVIDER_URL,
          token:
            process.env.PAPERLESS_API_TOKEN ?? process.env.DOCUMENT_PROVIDER_TOKEN,
          collection: process.env.COLLECTION_NAME ?? 'documents',
        },
      ];
    }

    return connectors.map((conn) => ({
      id: conn.id,
      type: conn.type,
      enabled: conn.enabled,
      url:
        conn.url ??
        (conn.type === 'paperless' ? process.env.PAPERLESS_API_URL : undefined),
      token:
        this.resolveEnv(conn.tokenEnv) ??
        (conn.type === 'paperless' ? process.env.PAPERLESS_API_TOKEN : undefined),
      collection: conn.collection ?? conn.id,
    }));
  }

  private vectorDbSlice(c: DocuMindConfig): Record<string, unknown> {
    const v = c.vectorDb;
    const h = c.hybridSearch;
    return {
      vector_db_type: v.type,
      collection_name: v.collection,
      embedding_provider: v.embeddingProvider,
      embedding_model: v.embeddingModel,
      reranker_provider: v.rerankerProvider,
      cross_encoder_model: v.crossEncoderModel,
      similarity_metric: v.similarityMetric,
      pgvector_url: v.pgvectorUrl ?? process.env.PGVECTOR_URL,
      keyword_method: h.keywordMethod,
      keyword_weight: h.keywordWeight,
      semantic_weight: h.semanticWeight,
      fts_language: h.ftsLanguage,
    };
  }

  private redactSecrets(config: DocuMindConfig): DocuMindConfig {
    const clone: DocuMindConfig = JSON.parse(JSON.stringify(config));
    clone.vectorDb.pgvectorUrl = this.redactUrl(clone.vectorDb.pgvectorUrl);
    for (const connector of clone.connectors) {
      connector.url = this.redactUrl(connector.url);
    }
    return clone;
  }

  private restoreUrlSecrets(input: unknown): unknown {
    if (!input || typeof input !== 'object') {
      return input;
    }
    const obj = input as Record<string, unknown>;
    const previous = this.config;

    if (obj.vectorDb && typeof obj.vectorDb === 'object') {
      const vectorDb = obj.vectorDb as Record<string, unknown>;
      vectorDb.pgvectorUrl = this.restoreUrl(
        vectorDb.pgvectorUrl as string | undefined,
        previous.vectorDb.pgvectorUrl,
      );
    }

    if (Array.isArray(obj.connectors)) {
      obj.connectors.forEach((connector, index) => {
        if (connector && typeof connector === 'object') {
          const entry = connector as Record<string, unknown>;
          entry.url = this.restoreUrl(
            entry.url as string | undefined,
            previous.connectors[index]?.url,
          );
        }
      });
    }

    return obj;
  }

  private redactUrl(url?: string): string | undefined {
    if (!url) {
      return url;
    }
    return url.replace(
      /^([a-z][a-z0-9+.-]*:\/\/[^:/@]+:)([^@]+)(@)/i,
      '$1***$3',
    );
  }

  private restoreUrl(
    incoming?: string,
    existing?: string,
  ): string | undefined {
    if (!incoming || !existing) {
      return incoming;
    }
    return incoming.includes(':***@') ? existing : incoming;
  }
}
