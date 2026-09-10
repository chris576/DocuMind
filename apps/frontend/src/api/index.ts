import { apiClient } from './client';
import type {
  AskRequestDto,
  AskResponseDto,
  IngestionRunDto,
  SearchRequestDto,
  SearchResult,
} from '@documind/shared';

export async function searchDocuments(
  dto: SearchRequestDto,
): Promise<SearchResult[]> {
  const { data } = await apiClient.post('/api/retrieval/search', dto);
  return data;
}

export async function askQuestion(dto: AskRequestDto): Promise<AskResponseDto> {
  const { data } = await apiClient.post('/api/generation/ask', dto);
  return data;
}

export async function runIngestion(dto: IngestionRunDto) {
  const { data } = await apiClient.post('/api/ingestion/run', dto);
  return data;
}

export async function runIngestionSync(dto: IngestionRunDto) {
  const { data } = await apiClient.post('/api/ingestion/run/sync', dto);
  return data;
}

export async function getIngestionStatus() {
  const { data } = await apiClient.get('/api/ingestion/status');
  return data;
}

export async function getRetrievalStatus() {
  const { data } = await apiClient.get('/api/retrieval/status');
  return data;
}

export async function getGenerationStatus() {
  const { data } = await apiClient.get('/api/generation/status');
  return data;
}
