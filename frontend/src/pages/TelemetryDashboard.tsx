import React, { useState, useEffect, useCallback } from 'react';
import {
  CpuChipIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:9898/api/v1';

async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('access_token');
  const resp = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!resp.ok) throw new Error(`API ${resp.status}`);
  return resp.json();
}

const TelemetryDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<Record<string, any>>({});
  const [agents, setAgents] = useState<any[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [m, a, t] = await Promise.all([
        apiRequest<Record<string, any>>('/telemetry/metrics'),
        apiRequest<{ items: any[] }>('/telemetry/agents'),
        apiRequest<{ items: any[] }>('/telemetry/judge/tasks'),
      ]);
      setMetrics(m);
      setAgents(a.items);
      setTasks(t.items);
      setLastRefresh(new Date());
    } catch {
      // Keep stale data
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, [loadData]);

  const statusIcon = (status: string) =>
    ['idle', 'active', 'healthy'].includes(status) ? (
      <CheckCircleIcon className="h-4 w-4 text-green-500" />
    ) : (
      <XCircleIcon className="h-4 w-4 text-red-500" />
    );

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <CpuChipIcon className="h-8 w-8 text-violet-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Telemetry Dashboard</h1>
            <p className="text-sm text-gray-500">Real-time system health and agent monitoring</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400">
            Auto-refresh: 15s · Last: {lastRefresh.toLocaleTimeString()}
          </span>
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            <ArrowPathIcon className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Total AI Requests', value: metrics.ai_requests?.total || 0, color: 'bg-violet-50 text-violet-700' },
          { label: 'AI Errors', value: metrics.ai_requests?.errors || 0, color: 'bg-red-50 text-red-700' },
          { label: 'Registered Agents', value: metrics.agents?.total || 0, color: 'bg-blue-50 text-blue-700' },
          { label: 'Event Bus Queue', value: metrics.event_bus?.queue_size || 0, color: 'bg-amber-50 text-amber-700' },
        ].map((card) => (
          <div key={card.label} className="bg-white border border-gray-200 rounded-xl p-4">
            <p className="text-2xl font-bold text-gray-900">{card.value}</p>
            <p className="text-sm text-gray-500 mt-1">{card.label}</p>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6 mb-6">
        {/* Agents table */}
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="text-base font-semibold text-gray-900">
              Registered Agents ({agents.length})
            </h2>
          </div>
          {agents.length === 0 ? (
            <p className="text-center py-8 text-gray-400 text-sm">No agents registered</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left px-4 py-2 text-gray-500 font-medium">Agent</th>
                    <th className="text-left px-4 py-2 text-gray-500 font-medium">Type</th>
                    <th className="text-left px-4 py-2 text-gray-500 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {agents.map((agent) => (
                    <tr key={agent.agent_id}>
                      <td className="px-4 py-2">
                        <p className="font-medium text-gray-900">{agent.name}</p>
                        <p className="text-xs text-gray-400 font-mono">{agent.agent_id}</p>
                      </td>
                      <td className="px-4 py-2 text-gray-600">{agent.type}</td>
                      <td className="px-4 py-2">
                        <span className="flex items-center gap-1">
                          {statusIcon(agent.status)}
                          <span className="capitalize">{agent.status}</span>
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Judge tasks */}
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="text-base font-semibold text-gray-900">
              Judge Task Queue ({tasks.length})
            </h2>
          </div>
          {tasks.length === 0 ? (
            <p className="text-center py-8 text-gray-400 text-sm">No tasks in queue</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left px-4 py-2 text-gray-500 font-medium">Task</th>
                    <th className="text-left px-4 py-2 text-gray-500 font-medium">Action</th>
                    <th className="text-left px-4 py-2 text-gray-500 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {tasks.map((task) => (
                    <tr key={task.task_id}>
                      <td className="px-4 py-2 font-mono text-xs text-gray-600">{task.task_id.slice(0, 8)}</td>
                      <td className="px-4 py-2 text-gray-600">{task.action}</td>
                      <td className="px-4 py-2">
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs capitalize ${
                          task.status === 'approved' ? 'bg-green-100 text-green-700' :
                          task.status === 'rejected' ? 'bg-red-100 text-red-700' :
                          'bg-yellow-100 text-yellow-700'
                        }`}>
                          {task.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Provider metrics */}
      {metrics.by_provider && Object.keys(metrics.by_provider).length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Provider Performance</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-4 py-2 text-gray-500 font-medium">Provider</th>
                  <th className="text-left px-4 py-2 text-gray-500 font-medium">Model</th>
                  <th className="text-right px-4 py-2 text-gray-500 font-medium">Requests</th>
                  <th className="text-right px-4 py-2 text-gray-500 font-medium">Errors</th>
                  <th className="text-right px-4 py-2 text-gray-500 font-medium">Avg Latency</th>
                  <th className="text-right px-4 py-2 text-gray-500 font-medium">Tokens</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {Object.entries(metrics.by_provider).flatMap(([provider, models]: [string, any]) =>
                  Object.entries(models).map(([model, stats]: [string, any]) => (
                    <tr key={`${provider}:${model}`}>
                      <td className="px-4 py-2 capitalize font-medium text-gray-800">{provider}</td>
                      <td className="px-4 py-2 font-mono text-xs text-gray-500">{model}</td>
                      <td className="px-4 py-2 text-right">{stats.requests}</td>
                      <td className="px-4 py-2 text-right text-red-500">{stats.errors}</td>
                      <td className="px-4 py-2 text-right">{stats.avg_latency_ms}ms</td>
                      <td className="px-4 py-2 text-right">{stats.total_tokens?.toLocaleString()}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default TelemetryDashboard;
