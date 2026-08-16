/**
 * Contract for document source connectors.
 *
 * A connector abstracts how documents are read from a specific document
 * management system (DMS), ERP, or other document source. Implementations
 * normalize their source-specific responses into the common shapes below so
 * that the rest of the application stays source-agnostic.
 */

/** Injection token that resolves to the currently active connector. */
export const DOCUMENT_CONNECTOR = 'DOCUMENT_CONNECTOR';

/**
 * Normalized representation of a document as returned by any connector.
 * The `id` is always a string — numeric IDs (e.g. Paperless) are converted
 * by the connector implementation.
 */
export interface DocumentRecord {
  id: string;
  title: string;
  /** Identifier of the connector that produced this record (e.g. "paperless"). */
  sourceType: string;
  createdAt?: string;
  updatedAt?: string;
  /** Source-specific fields that do not fit the common model. */
  metadata?: Record<string, unknown>;
}

/** Normalized text content of a document. */
export interface DocumentContent {
  id: string;
  content: string;
  mimeType?: string;
}

/** The strategy contract every document connector must implement. */
export interface DocumentConnector {
  /** Unique, stable identifier used for registry lookup and routing. */
  readonly type: string;

  listDocuments(): Promise<DocumentRecord[]>;
  getDocument(id: string): Promise<DocumentRecord>;
  getDocumentContent(id: string): Promise<DocumentContent>;
}
