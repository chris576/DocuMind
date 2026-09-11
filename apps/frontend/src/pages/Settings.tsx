import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getConfig, saveConfig } from '../api';

export default function Settings() {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState('');
  const [error, setError] = useState<string | null>(null);

  const { isLoading, isError } = useQuery({
    queryKey: ['config'],
    queryFn: async () => {
      const config = await getConfig();
      setDraft(JSON.stringify(config, null, 2));
      return config;
    },
  });

  const save = useMutation({
    mutationFn: saveConfig,
    onSuccess: (data) => {
      setDraft(JSON.stringify(data, null, 2));
      setError(null);
      queryClient.invalidateQueries({ queryKey: ['config'] });
    },
    onError: (e) =>
      setError(e instanceof Error ? e.message : 'Speichern fehlgeschlagen'),
  });

  const handleSave = () => {
    setError(null);
    try {
      save.mutate(JSON.parse(draft));
    } catch {
      setError('Ungültiges JSON');
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
        Einstellungen
      </h1>
      <p className="mt-2 text-gray-600 dark:text-gray-400">
        Konfiguration der Pipelines (LLM, Connectors, Vector-DB, Hybrid-Suche)
        als JSON.
      </p>
      {isLoading && <p className="mt-4 text-gray-500">Lade…</p>}
      {isError && (
        <p className="mt-4 text-red-500">Konfiguration nicht erreichbar.</p>
      )}
      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        spellCheck={false}
        aria-label="Konfiguration JSON"
        className="mt-4 w-full h-96 font-mono text-sm border border-gray-300 rounded-md p-3 text-gray-900 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
      />
      {error && <p className="mt-2 text-red-500">{error}</p>}
      <div className="mt-4 flex gap-2">
        <button
          onClick={handleSave}
          disabled={save.isPending}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {save.isPending ? 'Speichere…' : 'Speichern'}
        </button>
      </div>
    </div>
  );
}
