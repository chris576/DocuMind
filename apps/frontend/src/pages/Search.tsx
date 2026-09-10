import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { searchDocuments } from '../api';
import type { SearchResult } from '@documind/shared';

export default function Search() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const mutation = useMutation({
    mutationFn: searchDocuments,
    onSuccess: (data) => setResults(data),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    mutation.mutate({ query: query.trim() });
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Suche</h1>
      <p className="mt-2 text-gray-600 dark:text-gray-400">
        Dokumente im Archiv durchsuchen.
      </p>
      <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Suchbegriff…"
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-gray-900 dark:bg-gray-800 dark:border-gray-700 dark:text-white focus:outline-none focus:ring-blue-500"
        />
        <button
          type="submit"
          disabled={mutation.isPending}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          Suchen
        </button>
      </form>
      {mutation.isError && (
        <p className="mt-4 text-red-500">Fehler bei der Suche.</p>
      )}
      <ul className="mt-6 space-y-4">
        {results.map((r, i) => (
          <li
            key={i}
            className="bg-white dark:bg-gray-800 shadow rounded-lg p-4"
          >
            <div className="flex justify-between gap-4">
              <h3 className="font-semibold text-gray-900 dark:text-white">
                {r.title}
              </h3>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {r.correspondent}
                {r.date ? ` · ${r.date}` : ''}
              </span>
            </div>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              {r.snippet}
            </p>
            <span className="mt-2 inline-block text-xs text-gray-400">
              Score: {r.score.toFixed(3)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
