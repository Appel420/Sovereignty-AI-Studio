import React, { useEffect, useState } from 'react';

interface Org {
  id: number;
  name: string;
  created_at: string;
  owner_id: number;
  member_count?: number;
}

interface OrgListResponse {
  orgs: Org[];
  total: number;
}

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:9898/api/v1';

function getToken(): string | null {
  return localStorage.getItem('access_token');
}

function authHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const OrgView: React.FC = () => {
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newOrgName, setNewOrgName] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const fetchOrgs = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/org`, {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: OrgListResponse = await res.json();
      setOrgs(data.orgs);
    } catch (err: any) {
      setError(err.message || 'Failed to load organizations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrgs();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newOrgName.trim()) return;
    setCreating(true);
    setCreateError(null);
    try {
      const res = await fetch(`${API_BASE}/org`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders(),
        },
        body: JSON.stringify({ name: newOrgName.trim() }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      setNewOrgName('');
      await fetchOrgs();
    } catch (err: any) {
      setCreateError(err.message || 'Failed to create organization');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.75rem', marginBottom: '8px' }}>Organizations</h1>
      <p style={{ color: '#666', marginBottom: '24px' }}>
        Manage the organizations you belong to or create a new one.
      </p>

      {/* Create org form */}
      <form
        onSubmit={handleCreate}
        style={{
          display: 'flex',
          gap: '12px',
          marginBottom: '32px',
          alignItems: 'flex-start',
        }}
      >
        <div style={{ flex: 1 }}>
          <input
            type="text"
            value={newOrgName}
            onChange={(e) => setNewOrgName(e.target.value)}
            placeholder="Organization name"
            disabled={creating}
            style={{
              width: '100%',
              padding: '10px 14px',
              borderRadius: '6px',
              border: '1px solid #d1d5db',
              fontSize: '1rem',
              boxSizing: 'border-box',
            }}
          />
          {createError && (
            <p style={{ color: '#dc2626', fontSize: '0.875rem', marginTop: '4px' }}>
              {createError}
            </p>
          )}
        </div>
        <button
          type="submit"
          disabled={creating || !newOrgName.trim()}
          style={{
            padding: '10px 20px',
            borderRadius: '6px',
            background: '#2563eb',
            color: '#fff',
            border: 'none',
            fontSize: '1rem',
            cursor: creating ? 'not-allowed' : 'pointer',
            opacity: creating ? 0.7 : 1,
            whiteSpace: 'nowrap',
          }}
        >
          {creating ? 'Creating…' : 'Create Org'}
        </button>
      </form>

      {/* Org list */}
      {loading && <p>Loading organizations…</p>}
      {error && <p style={{ color: '#dc2626' }}>Error: {error}</p>}
      {!loading && !error && orgs.length === 0 && (
        <p style={{ color: '#6b7280' }}>
          You don't belong to any organizations yet. Create one above.
        </p>
      )}
      {!loading && orgs.length > 0 && (
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {orgs.map((org) => (
            <li
              key={org.id}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '16px',
                marginBottom: '12px',
                borderRadius: '8px',
                border: '1px solid #e5e7eb',
                background: '#fff',
              }}
            >
              <div>
                <strong style={{ fontSize: '1rem' }}>{org.name}</strong>
                {org.member_count !== undefined && (
                  <span style={{ color: '#6b7280', marginLeft: '12px', fontSize: '0.875rem' }}>
                    {org.member_count} member{org.member_count !== 1 ? 's' : ''}
                  </span>
                )}
              </div>
              <a
                href={`/orgs/${org.id}/team`}
                style={{ color: '#2563eb', fontSize: '0.875rem', textDecoration: 'none' }}
              >
                Manage Team →
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default OrgView;
