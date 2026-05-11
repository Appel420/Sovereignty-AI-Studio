import React, { useState, useEffect, useCallback } from 'react';
import {
  UserPlusIcon,
  UserMinusIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline';

const API_BASE = process.env.REACT_APP_API_URL || 'http://127.0.0.1:9899/api/v1';

interface Member {
  id: number;
  user_id: number;
  organization_id: number;
  role: string;
  is_active: boolean;
  joined_at: string;
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

const ROLE_COLORS: Record<string, string> = {
  owner: 'bg-amber-100 text-amber-700',
  admin: 'bg-indigo-100 text-indigo-700',
  member: 'bg-blue-100 text-blue-700',
  viewer: 'bg-gray-100 text-gray-600',
};

const MemberManager: React.FC<{ orgId: number }> = ({ orgId }) => {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showInvite, setShowInvite] = useState(false);
  const [inviteForm, setInviteForm] = useState({ user_id: '', role: 'member' });
  const [inviting, setInviting] = useState(false);
  const [removing, setRemoving] = useState<number | null>(null);

  const loadMembers = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiRequest<{ items: Member[] }>(`/org/${orgId}/members`);
      setMembers(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load members');
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    loadMembers();
  }, [loadMembers]);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteForm.user_id) return;
    setInviting(true);
    setError(null);
    try {
      await apiRequest(`/org/${orgId}/members`, {
        method: 'POST',
        body: JSON.stringify({
          user_id: parseInt(inviteForm.user_id),
          role: inviteForm.role,
        }),
      });
      setShowInvite(false);
      setInviteForm({ user_id: '', role: 'member' });
      await loadMembers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add member');
    } finally {
      setInviting(false);
    }
  };

  const handleRemove = async (userId: number) => {
    if (!confirm(`Remove this member from the organization?`)) return;
    setRemoving(userId);
    try {
      await apiRequest(`/org/${orgId}/members/${userId}`, { method: 'DELETE' });
      await loadMembers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove member');
    } finally {
      setRemoving(null);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-gray-900">
          Members ({members.length})
        </h2>
        <button
          onClick={() => setShowInvite(v => !v)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
        >
          <UserPlusIcon className="h-4 w-4" />
          Add Member
        </button>
      </div>

      {error && (
        <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {showInvite && (
        <form onSubmit={handleInvite} className="mb-4 p-4 bg-indigo-50 border border-indigo-200 rounded-xl">
          <div className="flex gap-3">
            <input
              type="number"
              required
              placeholder="User ID"
              value={inviteForm.user_id}
              onChange={(e) => setInviteForm(f => ({ ...f, user_id: e.target.value }))}
              className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
            <div className="relative">
              <select
                value={inviteForm.role}
                onChange={(e) => setInviteForm(f => ({ ...f, role: e.target.value }))}
                className="appearance-none px-3 pr-8 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              >
                <option value="owner">Owner</option>
                <option value="admin">Admin</option>
                <option value="member">Member</option>
                <option value="viewer">Viewer</option>
              </select>
              <ChevronDownIcon className="absolute right-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400 pointer-events-none" />
            </div>
            <button
              type="submit"
              disabled={inviting}
              className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              {inviting ? 'Adding…' : 'Add'}
            </button>
            <button
              type="button"
              onClick={() => setShowInvite(false)}
              className="px-4 py-2 text-sm border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="text-center py-6 text-gray-400 text-sm">Loading members…</p>
      ) : members.length === 0 ? (
        <p className="text-center py-6 text-gray-400 text-sm">No members yet</p>
      ) : (
        <div className="divide-y divide-gray-100">
          {members.map((member) => (
            <div key={member.id} className="flex items-center justify-between py-3">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-600 font-medium text-sm">
                  {member.user_id}
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-800">User #{member.user_id}</p>
                  <p className="text-xs text-gray-400">
                    Joined {new Date(member.joined_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-0.5 rounded-full capitalize ${ROLE_COLORS[member.role] || 'bg-gray-100 text-gray-600'}`}>
                  {member.role}
                </span>
                <button
                  onClick={() => handleRemove(member.user_id)}
                  disabled={removing === member.user_id}
                  className="p-1 text-gray-400 hover:text-red-500 disabled:opacity-40"
                  title="Remove member"
                >
                  <UserMinusIcon className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default MemberManager;
