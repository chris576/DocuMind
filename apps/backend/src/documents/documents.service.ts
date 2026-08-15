import { Injectable, HttpException, HttpStatus } from '@nestjs/common';
import axios from 'axios';

@Injectable()
export class DocumentsService {
  private readonly paperlessUrl = process.env.PAPERLESS_API_URL;
  private readonly paperlessToken = process.env.PAPERLESS_API_TOKEN;

  private get headers() {
    return {
      Authorization: `Token ${this.paperlessToken}`,
      'Content-Type': 'application/json',
    };
  }

  async findAll() {
    try {
      const response = await axios.get(`${this.paperlessUrl}/api/documents/`, {
        headers: this.headers,
      });
      return response.data;
    } catch (error) {
      throw new HttpException(
        'Failed to fetch documents',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  async findOne(id: number) {
    try {
      const response = await axios.get(`${this.paperlessUrl}/api/documents/${id}/`, {
        headers: this.headers,
      });
      return response.data;
    } catch (error) {
      throw new HttpException(
        'Failed to fetch document',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  async getContent(id: number) {
    try {
      const response = await axios.get(
        `${this.paperlessUrl}/api/documents/${id}/download/txt/`,
        { headers: this.headers },
      );
      return response.data;
    } catch (error) {
      throw new HttpException(
        'Failed to fetch document content',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  async processDocument(id: number) {
    // TODO: Implement document processing with AI
    return { status: 'processing', documentId: id };
  }
}
