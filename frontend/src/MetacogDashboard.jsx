import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function MetacogDashboard({ latestResult }) {
  const [systemStatus, setSystemStatus] = useState(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        setSystemStatus(data);
      } catch (e) { console.error(e); }
    };
    fetchStatus();
  }, [latestResult]);

  if (!latestResult) {
    return <div className="text-gray-500 text-center mt-20">Awaiting first query to build self-awareness...</div>;
  }

  const calData = systemStatus?.calibration_curve ? 
    Object.entries(systemStatus.calibration_curve).map(([conf, acc]) => ({
      confidence: parseFloat(conf),
      actual: acc,
      perfect: parseFloat(conf)
    })) : [];

  const cogMap = systemStatus?.cognitive_map?.quadrant_distribution || {};

  return (
    <div className="space-y-6">
      <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
        <h3 className="text-sm font-bold mb-4 text-gray-300">Calibration Curve (Confidence vs Accuracy)</h3>
        <p className="text-xs text-gray-500 mb-2">If perfect, the line matches the diagonal. Overconfidence = line falls below diagonal.</p>
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={calData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="confidence" stroke="#666" label={{ value: 'Confidence', position: 'insideBottom', offset: -5 }}/>
              <YAxis stroke="#666" label={{ value: 'Actual Acc.', angle: -90, position: 'insideLeft' }}/>
              <Tooltip />
              <Line type="monotone" dataKey="perfect" stroke="#555" strokeDasharray="5 5" name="Perfect Calibration" />
              <Line type="monotone" dataKey="actual" stroke="#818cf8" strokeWidth={2} name="System Reality" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
        <h3 className="text-sm font-bold mb-4 text-gray-300">Rumsfeld Matrix (Knowledge Health)</h3>
        <div className="grid grid-cols-2 gap-2 text-center">
          <div className="bg-green-900/20 border border-green-800 p-3 rounded">
            <div className="text-green-400 font-bold text-lg">{cogMap.KNOWN_KNOWN || 0}</div>
            <div className="text-xs text-green-600">Known Knowns (Safe)</div>
          </div>
          <div className="bg-red-900/20 border border-red-800 p-3 rounded">
            <div className="text-red-400 font-bold text-lg">{cogMap.UNKNOWN_KNOWN || 0}</div>
            <div className="text-xs text-red-600">Unknown Knowns (Danger!)</div>
          </div>
          <div className="bg-blue-900/20 border border-blue-800 p-3 rounded">
            <div className="text-blue-400 font-bold text-lg">{cogMap.KNOWN_UNKNOWN || 0}</div>
            <div className="text-xs text-blue-600">Known Unknowns (Cautious)</div>
          </div>
          <div className="bg-yellow-900/20 border border-yellow-800 p-3 rounded">
            <div className="text-yellow-400 font-bold text-lg">{cogMap.UNKNOWN_UNKNOWN || 0}</div>
            <div className="text-xs text-yellow-600">Unknown Unknowns (Ignorant)</div>
          </div>
        </div>
      </div>

      <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
        <h3 className="text-sm font-bold mb-2 text-gray-300">Metacognitive Metrics</h3>
        <div className="space-y-3">
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-gray-400">System Calibration Error (ECE)</span>
              <span className="text-white">{(latestResult.calibration_error * 100).toFixed(1)}%</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-1.5">
              <div className="bg-red-500 h-1.5 rounded-full" style={{width: `${latestResult.calibration_error * 100}%`}}></div>
            </div>
            <div className="text-xs text-gray-600 mt-1">Lower is better (0% = perfectly calibrated)</div>
          </div>
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-gray-400">2nd-Order Confidence (Trust in self)</span>
              <span className="text-cyan-400">{(latestResult.second_order_confidence * 100).toFixed(1)}%</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-1.5">
              <div className="bg-cyan-500 h-1.5 rounded-full" style={{width: `${latestResult.second_order_confidence * 100}%`}}></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
