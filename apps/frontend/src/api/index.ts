import { apiClient } from './client';
import type {
  SearchRequestDto,
  SearchResult,
} from '@documind/shared';

export async function searchDocuments(
  dto: SearchRequestDto,
): Promise<SearchResult[]> {
  const { data } = await apiClient.post('/api/retrieval/search', dto);
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

export async function getConfig(): Promise<unknown> {
  const { data } = await apiClient.get('/api/config');
  return data;
}

export async function saveConfig(config: unknown): Promise<unknown> {
  const { data } = await apiClient.put('/api/config', config);
  return data;
}
