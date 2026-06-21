import React, { useState } from 'react';
import ChatWindow from './ChatWindow';
import MetacogDashboard from './MetacogDashboard';

export default function App() {
  const [results, setResults] = useState([]);

  const addResult = (res) => {
    setResults(prev => [res, ...prev]);
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex">
      <div className="w-1/2 p-6 border-r border-gray-800 overflow-y-auto">
        <h1 className="text-3xl font-bold mb-2 flex items-center gap-2">
          <span className="text-indigo-400">◆</span> PRISM RAG
        </h1>
        <p className="text-gray-400 mb-6 text-sm">Metacognitive Retrieval-Augmented Generation</p>
        <ChatWindow onResult={addResult} pastResults={results} />
      </div>
      <div className="w-1/2 p-6 overflow-y-auto bg-gray-900/50">
        <h2 className="text-xl font-bold mb-4 text-gray-300">System Self-Awareness</h2>
        <MetacogDashboard latestResult={results[0]} />
      </div>
    </div>
  );
}
