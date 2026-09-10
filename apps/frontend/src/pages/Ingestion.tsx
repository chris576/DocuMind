import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getIngestionStatus, runIngestion, runIngestionSync } from '../api';

export default function Ingestion() {
  const queryClient = useQueryClient();
  const status = useQuery({
    queryKey: ['ingestion-status'],
    queryFn: getIngestionStatus,
    refetchInterval: 5000,
  });
  const run = useMutation({
    mutationFn: runIngestion,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['ingestion-status'] }),
  });
  const runSync = useMutation({
    mutationFn: runIngestionSync,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['ingestion-status'] }),
  });

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
        Ingestion
      </h1>
      <p className="mt-2 text-gray-600 dark:text-gray-400">
        Dokumente aus der Quelle einlesen und indexieren.
      </p>
      <div className="mt-4 flex gap-2">
        <button
          onClick={() => run.mutate({ force: false, checkNew: true })}
          disabled={run.isPending}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          Indexierung starten
        </button>
        <button
          onClick={() => runSync.mutate({ force: false, checkNew: true })}
          disabled={runSync.isPending}
          className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 disabled:opacity-50"
        >
          Synchron ausführen
        </button>
      </div>
      {(run.isError || runSync.isError) && (
        <p className="mt-4 text-red-500">Ingestion fehlgeschlagen.</p>
      )}
      <div className="mt-6 bg-white dark:bg-gray-800 shadow rounded-lg p-6">
        {status.isLoading ? (
          <p className="text-gray-500">Lade Status…</p>
        ) : status.isError ? (
          <p className="text-red-500">Status nicht erreichbar.</p>
        ) : (
          <pre className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
            {JSON.stringify(status.data, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}
