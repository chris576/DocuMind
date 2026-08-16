import { Injectable } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { ConfigService } from '@nestjs/config';
import { firstValueFrom } from 'rxjs';
import {
  DocumentConnector,
  DocumentContent,
  DocumentRecord,
} from './document-connector.interface';

/** Raw shape of a document returned by the Paperless-ngx REST API. */
interface PaperlessDocument {
  id: number;
  title?: string;
  created?: string;
  modified?: string;
  correspondent?: number | null;
  document_type?: number | null;
  tags?: number[];
  archive_serial_number?: string | null;
  original_file_name?: string | null;
  [key: string]: unknown;
}

interface PaperlessListResponse {
  results: PaperlessDocument[];
}

@Injectable()
export class PaperlessConnector implements DocumentConnector {
  readonly type = 'paperless';

  constructor(
    private readonly httpService: HttpService,
    private readonly configService: ConfigService,
  ) {}

  private get baseUrl(): string {
    return this.configService.get<string>('PAPERLESS_API_URL', '');
  }

  private get headers() {
    return {
      Authorization: `Token ${this.configService.get<string>('PAPERLESS_API_TOKEN', '')}`,
      'Content-Type': 'application/json',
    };
  }

  async listDocuments(): Promise<DocumentRecord[]> {
    const response = await firstValueFrom(
      this.httpService.get<PaperlessListResponse>(`${this.baseUrl}/api/documents/`, {
        headers: this.headers,
      }),
    );
    return (response.data.results ?? []).map((doc) => this.toRecord(doc));
  }

  async getDocument(id: string): Promise<DocumentRecord> {
    const response = await firstValueFrom(
      this.httpService.get<PaperlessDocument>(`${this.baseUrl}/api/documents/${id}/`, {
        headers: this.headers,
      }),
    );
    return this.toRecord(response.data);
  }

  async getDocumentContent(id: string): Promise<DocumentContent> {
    const response = await firstValueFrom(
      this.httpService.get<string>(`${this.baseUrl}/api/documents/${id}/download/txt/`, {
        headers: this.headers,
        responseType: 'text',
      }),
    );
    return {
      id,
      content: response.data,
      mimeType: 'text/plain',
    };
  }

  private toRecord(doc: PaperlessDocument): DocumentRecord {
    return {
      id: String(doc.id),
      title: doc.title ?? '',
      sourceType: this.type,
      createdAt: doc.created,
      updatedAt: doc.modified,
      metadata: {
        correspondent: doc.correspondent ?? null,
        document_type: doc.document_type ?? null,
        tags: doc.tags ?? [],
        archive_serial_number: doc.archive_serial_number ?? null,
        original_file_name: doc.original_file_name ?? null,
      },
    };
  }
}
