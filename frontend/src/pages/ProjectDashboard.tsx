import React, { useState, useEffect, useCallback } from 'react';
import {
  FolderIcon,
  PlusIcon,
  UserGroupIcon,
  ArrowLeftIcon,
} from '@heroicons/react/24/outline';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:9898/api/v1';

interface OrgProject {
  id: number;
  name: string;
  description?: string;
  project_type: string;
  status: string;
  is_archived: boolean;
  created_at: string;
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

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  inactive: 'bg-gray-100 text-gray-600',
  archived: 'bg-yellow-100 text-yellow-700',
};

const ProjectDashboard: React.FC<{ orgId?: number }> = ({ orgId: propOrgId }) => {
  const [orgId] = useState(() => {
    if (propOrgId) return propOrgId;
    const match = window.location.pathname.match(/\/organizations\/(\d+)/);
    return match ? parseInt(match[1]) : 1;
  });

  const [projects, setProjects] = useState<OrgProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', description: '', project_type: 'general' });
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const loadProjects = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiRequest<{ items: OrgProject[] }>(`/org/${orgId}/projects`);
      setProjects(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      await apiRequest(`/org/${orgId}/projects`, {
        method: 'POST',
        body: JSON.stringify(form),
      });
      setShowCreate(false);
      setForm({ name: '', description: '', project_type: 'general' });
      await loadProjects();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <a href="/organizations" className="text-gray-400 hover:text-gray-600">
            <ArrowLeftIcon className="h-5 w-5" />
          </a>
          <FolderIcon className="h-8 w-8 text-emerald-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Project Dashboard</h1>
            <p className="text-sm text-gray-500">Manage projects within this organization</p>
          </div>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
        >
          <PlusIcon className="h-4 w-4" />
          New Project
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {showCreate && (
        <div className="mb-6 p-6 bg-white border border-gray-200 rounded-xl shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Create Project</h2>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input
                type="text"
                required
                value={form.name}
                onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                placeholder="Project Alpha"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
              <select
                value={form.project_type}
                onChange={(e) => setForm(f => ({ ...f, project_type: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
              >
                <option value="general">General</option>
                <option value="ai">AI / ML</option>
                <option value="web_app">Web App</option>
                <option value="api">API</option>
                <option value="research">Research</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                value={form.description}
                onChange={(e) => setForm(f => ({ ...f, description: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                rows={2}
              />
            </div>
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={creating}
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50"
              >
                {creating ? 'Creating…' : 'Create'}
              </button>
              <button
                type="button"
                onClick={() => setShowCreate(false)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading projects…</div>
      ) : projects.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-dashed border-gray-300">
          <FolderIcon className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No projects yet</p>
          <p className="text-sm text-gray-400 mt-1">Create your first project to get started</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <div
              key={project.id}
              className="p-5 bg-white border border-gray-200 rounded-xl hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold text-gray-900">{project.name}</h3>
                <span className={`text-xs px-2 py-0.5 rounded-full capitalize ${STATUS_COLORS[project.status] || STATUS_COLORS.inactive}`}>
                  {project.status}
                </span>
              </div>
              {project.description && (
                <p className="text-sm text-gray-600 mb-3 line-clamp-2">{project.description}</p>
              )}
              <div className="flex items-center justify-between text-xs text-gray-400">
                <span className="capitalize bg-gray-100 px-2 py-0.5 rounded-full">
                  {project.project_type}
                </span>
                <span>{new Date(project.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ProjectDashboard;
