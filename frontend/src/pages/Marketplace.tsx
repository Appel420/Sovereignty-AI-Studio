import React, { useState, useEffect, useCallback } from 'react';
import {
  PuzzlePieceIcon,
  PlusIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';

const API_BASE = process.env.REACT_APP_API_URL || 'http://127.0.0.1:9899/api/v1';

interface Plugin {
  id: number;
  name: string;
  display_name: string;
  version: string;
  description?: string;
  author?: string;
  category?: string;
  status: string;
  is_enabled: boolean;
  health_status?: string;
  installed_at?: string;
}

async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('access_token');
  const resp = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
  if (!resp.ok) throw new Error(`API ${resp.status}: ${await resp.text()}`);
  return resp.json();
}

const STATUS_PILL: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  inactive: 'bg-gray-100 text-gray-600',
  error: 'bg-red-100 text-red-700',
};

const Marketplace: React.FC = () => {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activating, setActivating] = useState<string | null>(null);
  const [uninstalling, setUninstalling] = useState<string | null>(null);

  const loadPlugins = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiRequest<{ items: Plugin[] }>('/marketplace/');
      setPlugins(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load plugins');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPlugins();
  }, [loadPlugins]);

  const handleActivate = async (name: string) => {
    setActivating(name);
    try {
      await apiRequest(`/marketplace/${name}/activate`, {
        method: 'POST',
        body: JSON.stringify({ config: null }),
      });
      await loadPlugins();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Activation failed');
    } finally {
      setActivating(null);
    }
  };

  const handleUninstall = async (name: string) => {
    if (!confirm(`Uninstall plugin "${name}"?`)) return;
    setUninstalling(name);
    try {
      await apiRequest(`/marketplace/uninstall/${name}`, { method: 'DELETE' });
      await loadPlugins();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Uninstall failed');
    } finally {
      setUninstalling(null);
    }
  };

  const handleRunHealth = async () => {
    try {
      await apiRequest('/marketplace/health');
      await loadPlugins();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Health check failed');
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <PuzzlePieceIcon className="h-8 w-8 text-purple-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Agent Marketplace</h1>
            <p className="text-sm text-gray-500">Browse and manage sovereign AI agent plugins</p>
          </div>
        </div>
        <button
          onClick={handleRunHealth}
          className="flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
        >
          <ArrowPathIcon className="h-4 w-4" />
          Health Check
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600">✕</button>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading plugins…</div>
      ) : plugins.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-dashed border-gray-300">
          <PuzzlePieceIcon className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">No plugins installed</p>
          <p className="text-sm text-gray-400 mt-1 mb-4">
            Install plugins via the API or SDK to extend the platform
          </p>
          <a
            href="https://github.com/Appel420/Sovereignty-AI-Studio/blob/main/plugins/sdk/README.md"
            target="_blank"
            rel="noreferrer"
            className="text-sm text-purple-600 hover:underline"
          >
            View Plugin SDK docs →
          </a>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {plugins.map((plugin) => (
            <div key={plugin.id} className="bg-white border border-gray-200 rounded-xl p-5">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h3 className="font-semibold text-gray-900">{plugin.display_name}</h3>
                  <p className="text-xs text-gray-400 font-mono">{plugin.name} v{plugin.version}</p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full capitalize ${STATUS_PILL[plugin.status] || STATUS_PILL.inactive}`}>
                  {plugin.status}
                </span>
              </div>

              {plugin.description && (
                <p className="text-sm text-gray-600 mb-3 line-clamp-2">{plugin.description}</p>
              )}

              <div className="flex items-center justify-between text-xs text-gray-400 mb-4">
                <span>{plugin.author || 'Unknown author'}</span>
                <span className="capitalize bg-gray-100 px-2 py-0.5 rounded-full">
                  {plugin.category || 'general'}
                </span>
              </div>

              <div className="flex gap-2">
                {plugin.status !== 'active' && (
                  <button
                    onClick={() => handleActivate(plugin.name)}
                    disabled={activating === plugin.name}
                    className="flex items-center gap-1 px-3 py-1.5 text-xs bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                  >
                    <CheckCircleIcon className="h-3.5 w-3.5" />
                    {activating === plugin.name ? 'Activating…' : 'Activate'}
                  </button>
                )}
                <button
                  onClick={() => handleUninstall(plugin.name)}
                  disabled={uninstalling === plugin.name}
                  className="flex items-center gap-1 px-3 py-1.5 text-xs border border-red-200 text-red-600 rounded-lg hover:bg-red-50 disabled:opacity-50"
                >
                  <XCircleIcon className="h-3.5 w-3.5" />
                  {uninstalling === plugin.name ? 'Removing…' : 'Uninstall'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Marketplace;
