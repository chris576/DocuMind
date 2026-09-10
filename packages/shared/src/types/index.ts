export interface Document {
  id: number;
  title: string;
  content?: string;
  correspondent?: string;
  documentType?: string;
  tags?: string[];
  createdAt?: string;
  updatedAt?: string;
}

export interface SearchResult {
  title: string;
  correspondent: string;
  date: string;
  score: number;
  crossScore: number;
  snippet: string;
  docId?: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface RAGStatus {
  serverUp: boolean;
  dataLoaded: boolean;
  indexReady: boolean;
  chromaReady: boolean;
  bm25Ready: boolean;
  indexingStatus: {
    running: boolean;
    lastIndexed?: string;
    documentsCount: number;
    upToDate: boolean;
    message: string;
  };
}

export interface AIStatus {
  status: string;
  model?: string;
}
