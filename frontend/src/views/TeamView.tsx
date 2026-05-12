import React, { useEffect, useState } from 'react';

interface Member {
  id: number;
  org_id: number;
  user_id: number;
  role: string;
  joined_at: string;
}

interface MemberListResponse {
  members: Member[];
  total: number;
}

type Role = 'owner' | 'admin' | 'member';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:9898/api/v1';

function getToken(): string | null {
  return localStorage.getItem('access_token');
}

function authHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

interface TeamViewProps {
  orgId: number;
}

const ROLE_BADGE_COLORS: Record<string, string> = {
  owner: '#7c3aed',
  admin: '#2563eb',
  member: '#6b7280',
};

const TeamView: React.FC<TeamViewProps> = ({ orgId }) => {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Invite form state
  const [inviteUserId, setInviteUserId] = useState('');
  const [inviteRole, setInviteRole] = useState<Role>('member');
  const [inviting, setInviting] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteSuccess, setInviteSuccess] = useState<string | null>(null);

  const fetchMembers = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/org/${orgId}/members`, {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: MemberListResponse = await res.json();
      setMembers(data.members);
    } catch (err: any) {
      setError(err.message || 'Failed to load members');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMembers();
  }, [orgId]);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    const userId = parseInt(inviteUserId, 10);
    if (!userId || isNaN(userId)) {
      setInviteError('Please enter a valid user ID');
      return;
    }
    setInviting(true);
    setInviteError(null);
    setInviteSuccess(null);
    try {
      const res = await fetch(`${API_BASE}/org/${orgId}/members`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders(),
        },
        body: JSON.stringify({ user_id: userId, role: inviteRole }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      setInviteSuccess(`User ${userId} added as ${inviteRole}.`);
      setInviteUserId('');
      setInviteRole('member');
      await fetchMembers();
    } catch (err: any) {
      setInviteError(err.message || 'Failed to add member');
    } finally {
      setInviting(false);
    }
  };

  const formatDate = (iso: string): string => {
    try {
      return new Date(iso).toLocaleDateString();
    } catch {
      return iso;
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.75rem', marginBottom: '8px' }}>Team Management</h1>
      <p style={{ color: '#666', marginBottom: '24px' }}>
        Invite members and manage roles for organization #{orgId}.
      </p>

      {/* Invite form */}
      <form
        onSubmit={handleInvite}
        style={{
          display: 'flex',
          gap: '12px',
          marginBottom: '32px',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
        }}
      >
        <div>
          <input
            type="number"
            value={inviteUserId}
            onChange={(e) => setInviteUserId(e.target.value)}
            placeholder="User ID"
            disabled={inviting}
            style={{
              padding: '10px 14px',
              borderRadius: '6px',
              border: '1px solid #d1d5db',
              fontSize: '1rem',
              width: '140px',
            }}
          />
        </div>
        <div>
          <select
            value={inviteRole}
            onChange={(e) => setInviteRole(e.target.value as Role)}
            disabled={inviting}
            style={{
              padding: '10px 14px',
              borderRadius: '6px',
              border: '1px solid #d1d5db',
              fontSize: '1rem',
              background: '#fff',
              cursor: 'pointer',
            }}
          >
            <option value="member">Member</option>
            <option value="admin">Admin</option>
            <option value="owner">Owner</option>
          </select>
        </div>
        <button
          type="submit"
          disabled={inviting || !inviteUserId.trim()}
          style={{
            padding: '10px 20px',
            borderRadius: '6px',
            background: '#2563eb',
            color: '#fff',
            border: 'none',
            fontSize: '1rem',
            cursor: inviting ? 'not-allowed' : 'pointer',
            opacity: inviting ? 0.7 : 1,
          }}
        >
          {inviting ? 'Adding…' : 'Add Member'}
        </button>
        {inviteError && (
          <p style={{ color: '#dc2626', fontSize: '0.875rem', width: '100%', margin: '4px 0 0' }}>
            {inviteError}
          </p>
        )}
        {inviteSuccess && (
          <p style={{ color: '#16a34a', fontSize: '0.875rem', width: '100%', margin: '4px 0 0' }}>
            {inviteSuccess}
          </p>
        )}
      </form>

      {/* Member list */}
      {loading && <p>Loading members…</p>}
      {error && <p style={{ color: '#dc2626' }}>Error: {error}</p>}
      {!loading && !error && members.length === 0 && (
        <p style={{ color: '#6b7280' }}>No members yet. Invite someone above.</p>
      )}
      {!loading && members.length > 0 && (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
              <th style={{ textAlign: 'left', padding: '8px 12px', color: '#374151' }}>
                User ID
              </th>
              <th style={{ textAlign: 'left', padding: '8px 12px', color: '#374151' }}>
                Role
              </th>
              <th style={{ textAlign: 'left', padding: '8px 12px', color: '#374151' }}>
                Joined
              </th>
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                <td style={{ padding: '12px' }}>{m.user_id}</td>
                <td style={{ padding: '12px' }}>
                  <span
                    style={{
                      background: ROLE_BADGE_COLORS[m.role] || '#6b7280',
                      color: '#fff',
                      borderRadius: '12px',
                      padding: '2px 10px',
                      fontSize: '0.8rem',
                      fontWeight: 600,
                    }}
                  >
                    {m.role}
                  </span>
                </td>
                <td style={{ padding: '12px', color: '#6b7280', fontSize: '0.875rem' }}>
                  {formatDate(m.joined_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default TeamView;
