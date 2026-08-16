import { ChatMessage, SearchResult } from '../types/index.js';

export interface SearchRequestDto {
  query: string;
  fromDate?: string;
  toDate?: string;
  correspondent?: string;
}

export interface AskQuestionDto {
  question: string;
  maxSources?: number;
}

export interface ChatInitDto {
  documentId: number;
}

export interface ChatMessageDto {
  documentId: number;
  message: string;
}

export interface CreateTokenDto {
  name: string;
  scopes: string[];
  monthlyLimit?: number;
  expiresAt?: string;
}

export interface TokenResponseDto {
  id: number;
  token: string;
  name: string;
  prefix: string;
  scopes: string[];
  monthlyLimit?: number;
  expiresAt?: string;
}

export interface UsageResponseDto {
  tokenId: number;
  monthlyLimit?: number;
  monthlyUsage: {
    requestCount: number;
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

export interface StatusResponseDto {
  gateway: string;
  scopes: string[];
  rag: any;
  ai: any;
}

export interface RAGSearchResponseDto {
  results: SearchResult[];
}

export interface RAGAskResponseDto {
  answer: string;
  sources: Array<{
    title: string;
    correspondent: string;
    date: string;
    snippet: string;
    docId?: number;
  }>;
  metrics?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

export interface ChatInitResponseDto {
  documentTitle: string;
  initialized: boolean;
}

export interface ChatMessageResponseDto {
  content: string;
  done: boolean;
}
