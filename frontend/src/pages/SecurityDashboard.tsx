import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldCheckIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  UserCircleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import AuditLogTable from '../components/AuditLogTable';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:9899/api/v1';

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

interface MetricCard {
  label: string;
  value: string | number;
  icon: React.ElementType;
  color: string;
}

const SecurityDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const loadMetrics = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiRequest<Record<string, any>>('/telemetry/metrics');
      setMetrics(data);
      setLastRefresh(new Date());
    } catch {
      // Keep stale data
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMetrics();
    const interval = setInterval(loadMetrics, 30000);
    return () => clearInterval(interval);
  }, [loadMetrics]);

  const judgeData = metrics.judge || {};
  const agentData = metrics.agents || {};

  const cards: MetricCard[] = [
    {
      label: 'Active Agents',
      value: agentData.total || 0,
      icon: UserCircleIcon,
      color: 'text-blue-600 bg-blue-50',
    },
    {
      label: 'Pending Tasks',
      value: judgeData.by_status?.pending || 0,
      icon: ClockIcon,
      color: 'text-yellow-600 bg-yellow-50',
    },
    {
      label: 'AI Errors (session)',
      value: metrics.ai_requests?.errors || 0,
      icon: ExclamationTriangleIcon,
      color: 'text-red-600 bg-red-50',
    },
    {
      label: 'Locked Resources',
      value: judgeData.locked_resources || 0,
      icon: ShieldCheckIcon,
      color: 'text-green-600 bg-green-50',
    },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <ShieldCheckIcon className="h-8 w-8 text-slate-700" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Security Dashboard</h1>
            <p className="text-sm text-gray-500">
              Audit logs, sessions, and permission overview
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400">
            Last updated: {lastRefresh.toLocaleTimeString()}
          </span>
          <button
            onClick={loadMetrics}
            disabled={loading}
            className="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            <ArrowPathIcon className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {cards.map((card) => (
          <div key={card.label} className="bg-white border border-gray-200 rounded-xl p-4">
            <div className={`inline-flex p-2 rounded-lg ${card.color} mb-3`}>
              <card.icon className="h-5 w-5" />
            </div>
            <p className="text-2xl font-bold text-gray-900">{card.value}</p>
            <p className="text-sm text-gray-500">{card.label}</p>
          </div>
        ))}
      </div>

      {/* Provider breakdown */}
      {metrics.by_provider && Object.keys(metrics.by_provider).length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-5 mb-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">AI Provider Activity</h2>
          <div className="space-y-3">
            {Object.entries(metrics.by_provider).map(([provider, models]: [string, any]) => (
              <div key={provider}>
                <p className="text-sm font-medium text-gray-700 capitalize mb-1">{provider}</p>
                {Object.entries(models).map(([model, stats]: [string, any]) => (
                  <div key={model} className="flex items-center justify-between text-sm text-gray-600 pl-4">
                    <span className="font-mono text-xs text-gray-500">{model}</span>
                    <div className="flex gap-4 text-xs">
                      <span>{stats.requests} calls</span>
                      <span className="text-red-500">{stats.errors} errors</span>
                      <span>{stats.avg_latency_ms}ms avg</span>
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Audit log table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-900">Recent Audit Logs</h2>
        </div>
        <AuditLogTable />
      </div>
    </div>
  );
};

export default SecurityDashboard;
