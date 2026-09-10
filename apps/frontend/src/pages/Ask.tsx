import { useState } from 'react';
import { API_BASE } from '../api/client';

export default function Ask() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || streaming) return;
    setAnswer('');
    setError('');
    setStreaming(true);
    try {
      const res = await fetch(`${API_BASE}/api/generation/ask/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question.trim() }),
      });
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';
        for (const line of lines) {
          if (!line.startsWith('data:')) continue;
          const payload = line.slice(5).trim();
          if (payload === '[DONE]') continue;
          if (payload.startsWith('[ERROR]')) {
            setError(payload);
            continue;
          }
          setAnswer((prev) => prev + payload);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setStreaming(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
        Frage/Antwort
      </h1>
      <p className="mt-2 text-gray-600 dark:text-gray-400">
        Stelle eine Frage zu deinen Dokumenten.
      </p>
      <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Deine Frage…"
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-gray-900 dark:bg-gray-800 dark:border-gray-700 dark:text-white focus:outline-none focus:ring-blue-500"
        />
        <button
          type="submit"
          disabled={streaming}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {streaming ? 'Antworte…' : 'Fragen'}
        </button>
      </form>
      {error && <p className="mt-4 text-red-500">{error}</p>}
      {answer && (
        <div className="mt-6 bg-white dark:bg-gray-800 shadow rounded-lg p-6">
          <p className="whitespace-pre-wrap text-gray-900 dark:text-white">
            {answer}
          </p>
        </div>
      )}
    </div>
  );
}
