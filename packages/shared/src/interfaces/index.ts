import { SearchResult, ChatMessage } from '../types';

export interface IVectorDB {
  initialize(): Promise<boolean>;
  addDocuments(documents: Array<{
    id: string;
    title: string;
    content: string;
    metadata?: Record<string, any>;
  }>): Promise<void>;
  search(query: string, topK?: number): Promise<SearchResult[]>;
  deleteCollection(): Promise<void>;
  getStatus(): Promise<{ ready: boolean; documentCount: number }>;
}

export interface ILLMProvider {
  generateText(prompt: string, options?: {
    maxTokens?: number;
    temperature?: number;
  }): Promise<string>;
  generateStream(prompt: string, options?: {
    maxTokens?: number;
    temperature?: number;
  }): AsyncIterable<string>;
  checkStatus(): Promise<{ status: string; model?: string }>;
}

export interface IAuthService {
  validateToken(token: string): Promise<{
    userId: number;
    scopes: string[];
  } | null>;
  generateToken(payload: {
    userId: number;
    scopes: string[];
  }): string;
}

export interface IMessageQueue {
  publish(queue: string, message: any): Promise<void>;
  consume(queue: string, handler: (message: any) => Promise<void>): Promise<void>;
  close(): Promise<void>;
}

export interface IRetrievalService {
  search(query: string, options?: {
    fromDate?: string;
    toDate?: string;
    correspondent?: string;
  }): Promise<SearchResult[]>;
}

export interface IGenerationService {
  generateAnswer(question: string, context: string, options?: {
    maxSources?: number;
  }): Promise<{
    answer: string;
    sources: any[];
    metrics?: {
      promptTokens: number;
      completionTokens: number;
      totalTokens: number;
    };
  }>;
}

export interface IIngestionService {
  ingestDocuments(documents: Array<{
    id: number;
    title: string;
    content: string;
    metadata?: Record<string, any>;
  }>): Promise<void>;
  getStatus(): Promise<{
    running: boolean;
    lastIndexed?: string;
    documentsCount: number;
  }>;
}
