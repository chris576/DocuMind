import { useQuery } from '@tanstack/react-query';
import {
  getGenerationStatus,
  getIngestionStatus,
  getRetrievalStatus,
} from '../api';

function StatusCard({
  title,
  icon,
  loading,
  error,
  data,
}: {
  title: string;
  icon: string;
  loading: boolean;
  error: boolean;
  data: unknown;
}) {
  return (
    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-5">
      <div className="flex items-center mb-3">
        <span className="text-2xl">{icon}</span>
        <h2 className="ml-3 text-lg font-semibold text-gray-900 dark:text-white">
          {title}
        </h2>
      </div>
      {loading ? (
        <p className="text-gray-500">Lade…</p>
      ) : error ? (
        <p className="text-red-500">nicht erreichbar</p>
      ) : (
        <pre className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}

export default function Dashboard() {
  const ingestion = useQuery({
    queryKey: ['ingestion-status'],
    queryFn: getIngestionStatus,
    refetchInterval: 10000,
  });
  const retrieval = useQuery({
    queryKey: ['retrieval-status'],
    queryFn: getRetrievalStatus,
  });
  const generation = useQuery({
    queryKey: ['generation-status'],
    queryFn: getGenerationStatus,
  });

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
        Dashboard
      </h1>
      <p className="mt-2 text-gray-600 dark:text-gray-400">
        Status der drei Pipelines.
      </p>
      <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-3">
        <StatusCard
          title="Ingestion"
          icon="📥"
          loading={ingestion.isLoading}
          error={ingestion.isError}
          data={ingestion.data}
        />
        <StatusCard
          title="Retrieval"
          icon="🔍"
          loading={retrieval.isLoading}
          error={retrieval.isError}
          data={retrieval.data}
        />
        <StatusCard
          title="Generation"
          icon="✨"
          loading={generation.isLoading}
          error={generation.isError}
          data={generation.data}
        />
      </div>
    </div>
  );
}
