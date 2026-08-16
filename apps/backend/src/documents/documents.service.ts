import { Inject, Injectable, HttpException, HttpStatus } from '@nestjs/common';
import { DOCUMENT_CONNECTOR } from './connectors/document-connector.interface';
import type {
  DocumentConnector,
  DocumentRecord,
  DocumentContent,
} from './connectors/document-connector.interface';

/**
 * Facade over the active {@link DocumentConnector}.
 *
 * This service does not know which document source it talks to — it delegates
 * to the connector resolved via the {@link DOCUMENT_CONNECTOR} injection token
 * and maps connector failures to consistent HTTP errors.
 */
@Injectable()
export class DocumentsService {
  constructor(
    @Inject(DOCUMENT_CONNECTOR) private readonly connector: DocumentConnector,
  ) {}

  async findAll(): Promise<DocumentRecord[]> {
    return this.handle(
      () => this.connector.listDocuments(),
      'Failed to fetch documents',
    );
  }

  async findOne(id: string): Promise<DocumentRecord> {
    return this.handle(
      () => this.connector.getDocument(id),
      'Failed to fetch document',
    );
  }

  async getContent(id: string): Promise<DocumentContent> {
    return this.handle(
      () => this.connector.getDocumentContent(id),
      'Failed to fetch document content',
    );
  }

  async processDocument(id: string) {
    // TODO: Implement document processing with AI (delegate to ingestion pipeline).
    return { status: 'processing', documentId: id };
  }

  private async handle<T>(fn: () => Promise<T>, message: string): Promise<T> {
    try {
      return await fn();
    } catch (error) {
      throw new HttpException(message, HttpStatus.INTERNAL_SERVER_ERROR);
    }
  }
}
