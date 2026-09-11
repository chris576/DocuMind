import { SearchResult } from '../types/index.js';

export interface SearchRequestDto {
  query: string;
  namespace?: string;
  fromDate?: string;
  toDate?: string;
  correspondent?: string;
  maxResults?: number;
}

export interface AskRequestDto {
  question: string;
  namespace?: string;
  maxTokens?: number;
  temperature?: number;
}

export interface AskResponseDto {
  answer: string;
  sources: SearchResult[];
  metrics?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
  model?: string;
  provider?: string;
}

export interface IngestionRunDto {
  force?: boolean;
  checkNew?: boolean;
  namespace?: string;
}

export interface IngestionStatusDto {
  running: boolean;
  lastIndexed?: string;
  documentsCount: number;
  upToDate: boolean;
  message: string;
}

export interface ChatInitRequestDto {
  documentId?: number;
  documentTitle?: string;
  documentContent?: string;
  namespace?: string;
}

export interface ChatInitResponseDto {
  chatId: string;
  status: string;
}

export interface ChatMessageRequestDto {
  chatId: string;
  message: string;
  namespace?: string;
}

export interface ChatMessageResponseDto {
  chatId: string;
  message: string;
  role: string;
}
