import { Injectable } from '@nestjs/common';

export interface PipelineEntry {
  namespace?: string;
  collection?: string;
  ingestionUrl?: string;
  retrievalUrl?: string;
  generationUrl?: string;
}

export interface ResolvedPipeline {
  namespace: string;
  collection: string;
  ingestionUrl: string;
  retrievalUrl: string;
  generationUrl: string;
}

const DEFAULT_NAMESPACE = 'paperless';

@Injectable()
export class PipelineRegistry {
  private readonly entries = new Map<string, ResolvedPipeline>();

  constructor() {
    for (const entry of this.loadEntries()) {
      const resolved = this.resolveEntry(entry);
      this.entries.set(resolved.namespace, resolved);
    }
  }

  /**
   * Resolve a namespace to its pipeline endpoints. Falls back to the default
   * namespace when none is given; throws when the namespace is unknown.
   */
  resolve(namespace?: string): ResolvedPipeline {
    const ns = (namespace ?? '').trim() || DEFAULT_NAMESPACE;
    const entry = this.entries.get(ns);
    if (!entry) {
      throw new Error(
        `Unknown namespace "${ns}". Available: ${this.listNamespaces().join(', ') || '(none)'}`,
      );
    }
    return entry;
  }

  list(): ResolvedPipeline[] {
    return [...this.entries.values()];
  }

  listNamespaces(): string[] {
    return [...this.entries.keys()];
  }

  private loadEntries(): PipelineEntry[] {
    const raw = process.env.PIPELINE_REGISTRY_JSON;
    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          return parsed as PipelineEntry[];
        }
      } catch {
        // Fall through to the single default entry below.
      }
    }

    return [
      {
        namespace: DEFAULT_NAMESPACE,
        ingestionUrl: process.env.INGESTION_PIPELINE_URL,
        retrievalUrl: process.env.RETRIEVAL_PIPELINE_URL,
        generationUrl: process.env.GENERATION_PIPELINE_URL,
      },
    ];
  }

  private resolveEntry(entry: PipelineEntry): ResolvedPipeline {
    const namespace = entry.namespace?.trim() || DEFAULT_NAMESPACE;
    return {
      namespace,
      collection:
        entry.collection ||
        (namespace === DEFAULT_NAMESPACE
          ? process.env.COLLECTION_NAME || 'documents'
          : namespace),
      ingestionUrl:
        entry.ingestionUrl ||
        process.env.INGESTION_PIPELINE_URL ||
        'http://localhost:8001',
      retrievalUrl:
        entry.retrievalUrl ||
        process.env.RETRIEVAL_PIPELINE_URL ||
        'http://localhost:8002',
      generationUrl:
        entry.generationUrl ||
        process.env.GENERATION_PIPELINE_URL ||
        'http://localhost:8003',
    };
  }
}
