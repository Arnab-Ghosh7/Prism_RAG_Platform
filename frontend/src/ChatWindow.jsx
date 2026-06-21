import React, { useState } from 'react';
import { Send, Upload, ThumbsUp, ThumbsDown } from 'lucide-react';

export default function ChatWindow({ onResult, pastResults }) {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [docText, setDocText] = useState('');

  const handleQuery = async (e) => {
    e.preventDefault();
    if (!query) return;
    setLoading(true);
    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });
      const data = await res.json();
      onResult(data);
      setQuery('');
    } catch (err) { console.error(err); }
    setLoading(false);
  };

  const handleIngest = async () => {
    if (!docText) return;
    try {
      await fetch('/api/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ texts: [docText], metadatas: [{ source: 'user-input' }] })
      });
      setDocText('');
      alert('Knowledge ingested into vector DB!');
    } catch (err) { console.error(err); }
  };

  const handleFeedback = async (id, accuracy) => {
    await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ interaction_id: id, accuracy })
    });
    alert('Feedback recorded! Metacognitive state calibrated.');
  };

  const getQuadrantColor = (q) => {
    const map = {
      'KNOWN_KNOWN': 'bg-green-500/20 text-green-400 border-green-500',
      'KNOWN_UNKNOWN': 'bg-blue-500/20 text-blue-400 border-blue-500',
      'UNKNOWN_KNOWN': 'bg-red-500/20 text-red-400 border-red-500',
      'UNKNOWN_UNKNOWN': 'bg-yellow-500/20 text-yellow-400 border-yellow-500'
    };
    return map[q] || 'bg-gray-500';
  };

  return (
    <div className="space-y-6">
      <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
        <h3 className="text-sm font-semibold mb-2 text-gray-300">1. Ingest Knowledge (RAG Context)</h3>
        <textarea 
          className="w-full bg-gray-900 p-2 rounded text-sm h-20 border border-gray-600 focus:outline-none focus:border-indigo-500"
          placeholder="Paste text for the AI to learn and retrieve from..."
          value={docText}
          onChange={e => setDocText(e.target.value)}
        />
        <button onClick={handleIngest} className="mt-2 flex items-center gap-2 bg-gray-700 hover:bg-gray-600 px-3 py-1 rounded text-sm">
          <Upload size={14}/> Upload Context
        </button>
      </div>

      <form onSubmit={handleQuery} className="flex gap-2">
        <input 
          type="text" 
          className="flex-1 bg-gray-800 border border-gray-700 rounded px-4 py-2 focus:outline-none focus:border-indigo-500"
          placeholder="Ask a question based on the context..."
          value={query}
          onChange={e => setQuery(e.target.value)}
        />
        <button type="submit" disabled={loading} className="bg-indigo-600 hover:bg-indigo-500 px-4 py-2 rounded flex items-center gap-2 disabled:opacity-50">
          <Send size={16}/> {loading ? 'Thinking...' : 'Ask'}
        </button>
      </form>

      <div className="space-y-4 mt-6">
        {pastResults.map((res) => (
          <div key={res.interaction_id} className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
            <div className="flex justify-between items-start mb-2">
              <div className={`text-xs px-2 py-1 rounded border ${getQuadrantColor(res.cognitive_quadrant)}`}>
                {res.cognitive_quadrant.replace(/_/g, ' ')}
              </div>
              <div className="flex gap-1">
                <button onClick={() => handleFeedback(res.interaction_id, 1.0)} className="p-1 hover:text-green-400"><ThumbsUp size={14}/></button>
                <button onClick={() => handleFeedback(res.interaction_id, 0.0)} className="p-1 hover:text-red-400"><ThumbsDown size={14}/></button>
              </div>
            </div>
            <p className="text-sm text-gray-200 mb-2">{res.answer}</p>
            
            {res.context_used && (
              <div className="mt-2 bg-gray-900 p-2 rounded text-xs text-gray-400 border-l-2 border-indigo-400">
                <span className="font-bold text-indigo-400">RAG Context Used:</span> {res.context_used}
              </div>
            )}

            <div className="grid grid-cols-3 gap-2 mt-3 text-xs">
              <div className="bg-gray-900 p-2 rounded">
                <div className="text-gray-500">Raw Conf</div>
                <div className="font-mono text-white">{(res.raw_confidence * 100).toFixed(0)}%</div>
              </div>
              <div className="bg-gray-900 p-2 rounded">
                <div className="text-gray-500">Adjusted Conf</div>
                <div className="font-mono text-indigo-400">{(res.adjusted_confidence * 100).toFixed(0)}%</div>
              </div>
              <div className="bg-gray-900 p-2 rounded">
                <div className="text-gray-500">Retrieval Conf</div>
                <div className="font-mono text-cyan-400">{(res.retrieval_confidence * 100).toFixed(0)}%</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
