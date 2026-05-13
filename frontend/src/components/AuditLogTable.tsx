import React, { useState, useEffect, useCallback } from 'react';
import { FunnelIcon } from '@heroicons/react/24/outline';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:9898/api/v1';

interface AuditLogEntry {
  id: number;
  actor_id?: number;
  actor_email?: string;
  action: string;
  resource_type?: string;
  resource_id?: string;
  details?: string;
  ip_address?: string;
  status: string;
  created_at: string;
}

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

const STATUS_PILL: Record<string, string> = {
  success: 'bg-green-100 text-green-700',
  failure: 'bg-red-100 text-red-700',
};

const AuditLogTable: React.FC<{
  initialFilter?: string;
  compact?: boolean;
}> = ({ initialFilter, compact = false }) => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [filters, setFilters] = useState({
    action: initialFilter || '',
    status: '',
    since: '',
    until: '',
  });
  const [page, setPage] = useState(0);
  const limit = compact ? 10 : 25;

  const buildQuery = useCallback(() => {
    const params = new URLSearchParams();
    params.set('limit', String(limit));
    params.set('offset', String(page * limit));
    if (filters.action) params.set('action', filters.action);
    if (filters.status) params.set('status', filters.status);
    if (filters.since) params.set('since', filters.since);
    if (filters.until) params.set('until', filters.until);
    return params.toString();
  }, [filters, page, limit]);

  const loadLogs = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiRequest<{ items: AuditLogEntry[]; total: number }>(
        `/audit/logs?${buildQuery()}`
      );
      setLogs(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  }, [buildQuery]);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  const handleFilterChange = (key: string, value: string) => {
    setFilters(f => ({ ...f, [key]: value }));
    setPage(0);
  };

  return (
    <div>
      {/* Filters */}
      {!compact && (
        <div className="px-5 py-3 border-b border-gray-100 flex flex-wrap gap-3 bg-gray-50">
          <div className="flex items-center gap-2">
            <FunnelIcon className="h-4 w-4 text-gray-400" />
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Filter</span>
          </div>
          <input
            type="text"
            placeholder="Action (e.g. org.create)"
            value={filters.action}
            onChange={(e) => handleFilterChange('action', e.target.value)}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
          />
          <select
            value={filters.status}
            onChange={(e) => handleFilterChange('status', e.target.value)}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All statuses</option>
            <option value="success">Success</option>
            <option value="failure">Failure</option>
          </select>
          <input
            type="datetime-local"
            value={filters.since}
            onChange={(e) => handleFilterChange('since', e.target.value)}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
            title="Since"
          />
          <input
            type="datetime-local"
            value={filters.until}
            onChange={(e) => handleFilterChange('until', e.target.value)}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
            title="Until"
          />
        </div>
      )}

      {error && (
        <div className="px-5 py-3 text-sm text-red-600 bg-red-50 border-b border-red-100">
          {error}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left px-4 py-2.5 text-gray-500 font-medium">Time</th>
              <th className="text-left px-4 py-2.5 text-gray-500 font-medium">Actor</th>
              <th className="text-left px-4 py-2.5 text-gray-500 font-medium">Action</th>
              <th className="text-left px-4 py-2.5 text-gray-500 font-medium">Resource</th>
              <th className="text-left px-4 py-2.5 text-gray-500 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {loading ? (
              <tr>
                <td colSpan={5} className="text-center py-8 text-gray-400">Loading…</td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center py-8 text-gray-400">No audit logs found</td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50/50">
                  <td className="px-4 py-2.5 text-xs text-gray-400 whitespace-nowrap">
                    {log.created_at ? new Date(log.created_at).toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="text-gray-700">{log.actor_email || `#${log.actor_id}` || 'system'}</span>
                  </td>
                  <td className="px-4 py-2.5">
                    <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded font-mono">{log.action}</code>
                  </td>
                  <td className="px-4 py-2.5 text-gray-600 text-xs">
                    {log.resource_type && (
                      <span>
                        {log.resource_type}
                        {log.resource_id && <span className="text-gray-400"> #{log.resource_id}</span>}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs capitalize ${STATUS_PILL[log.status] || 'bg-gray-100 text-gray-600'}`}>
                      {log.status}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {!compact && total > limit && (
        <div className="px-5 py-3 border-t border-gray-100 flex items-center justify-between text-sm text-gray-600">
          <span>
            {page * limit + 1}–{Math.min((page + 1) * limit, total)} of {total}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-3 py-1 border border-gray-300 rounded disabled:opacity-40 hover:bg-gray-50"
            >
              ← Prev
            </button>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={(page + 1) * limit >= total}
              className="px-3 py-1 border border-gray-300 rounded disabled:opacity-40 hover:bg-gray-50"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default AuditLogTable;
