-- Sovereignty AI Studio — Full PostgreSQL Schema
-- Run: psql -U <user> -d <database> -f db/schema.sql
-- All UUIDs generated server-side; no application-generated IDs.

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ──────────────────────────────────────────────────────────────────────────
-- Core identity tables
-- ──────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT        UNIQUE NOT NULL,
    username        TEXT        UNIQUE,                    -- nullable for SSO/migration compat
    full_name       TEXT,
    hashed_password TEXT,                                  -- NULL if SSO-only login
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    is_verified     BOOLEAN     NOT NULL DEFAULT FALSE,
    avatar_url      TEXT,
    bio             TEXT,
    -- Presence / online status
    status          TEXT        NOT NULL DEFAULT 'offline',
    last_seen       TIMESTAMP,
    -- Subscription/Plan info
    subscription_plan        TEXT  NOT NULL DEFAULT 'free',
    subscription_expires_at  TIMESTAMP,
    -- Usage tracking
    total_generations        INT   NOT NULL DEFAULT 0,
    monthly_generations      INT   NOT NULL DEFAULT 0,
    last_generation_reset    TIMESTAMP DEFAULT NOW(),
    -- Timestamps
    created_at  TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP   NOT NULL DEFAULT NOW(),
    last_login  TIMESTAMP
);

CREATE TABLE IF NOT EXISTS organizations (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT        NOT NULL,
    slug        TEXT        UNIQUE,
    plan        TEXT        NOT NULL DEFAULT 'standard',
    created_at  TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS memberships (
    user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_id      UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role        TEXT        NOT NULL DEFAULT 'member',
    joined_at   TIMESTAMP   NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, org_id)
);

-- ──────────────────────────────────────────────────────────────────────────
-- Project layer
-- ──────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS projects (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name        TEXT        NOT NULL,
    description TEXT,
    created_at  TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS project_permissions (
    user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id  UUID        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    role        TEXT        NOT NULL DEFAULT 'viewer',
    granted_at  TIMESTAMP   NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, project_id)
);

-- ──────────────────────────────────────────────────────────────────────────
-- Usage & billing tracking
-- ──────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS usage (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        REFERENCES users(id) ON DELETE SET NULL,
    org_id      UUID        REFERENCES organizations(id) ON DELETE SET NULL,
    project_id  UUID        REFERENCES projects(id) ON DELETE SET NULL,
    tokens      INT         NOT NULL DEFAULT 0,
    provider    TEXT        NOT NULL DEFAULT 'sovereign',
    model       TEXT,
    created_at  TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS usage_org_idx      ON usage(org_id);
CREATE INDEX IF NOT EXISTS usage_user_idx     ON usage(user_id);
CREATE INDEX IF NOT EXISTS usage_project_idx  ON usage(project_id);
CREATE INDEX IF NOT EXISTS usage_created_idx  ON usage(created_at);

-- ──────────────────────────────────────────────────────────────────────────
-- Session store
-- ──────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sessions (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        REFERENCES users(id) ON DELETE CASCADE,
    data        JSONB,
    expires_at  TIMESTAMP,
    created_at  TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS sessions_user_idx    ON sessions(user_id);
CREATE INDEX IF NOT EXISTS sessions_expires_idx ON sessions(expires_at);

-- ──────────────────────────────────────────────────────────────────────────
-- Immutable audit log
-- ──────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS audit_logs (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID,                            -- nullable for system actions
    action      TEXT        NOT NULL,
    resource    TEXT,
    details     JSONB,
    ip_address  TEXT,
    created_at  TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS audit_user_idx    ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS audit_action_idx  ON audit_logs(action);
CREATE INDEX IF NOT EXISTS audit_created_idx ON audit_logs(created_at);

-- Prevent UPDATE/DELETE on audit_logs (append-only integrity)
CREATE OR REPLACE RULE audit_no_update AS ON UPDATE TO audit_logs
    DO INSTEAD NOTHING;
CREATE OR REPLACE RULE audit_no_delete AS ON DELETE TO audit_logs
    DO INSTEAD NOTHING;

-- ──────────────────────────────────────────────────────────────────────────
-- Role assignments (for dashboard roles beyond the basic member/admin roles)
-- ──────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS role_assignments (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_key    TEXT        NOT NULL,
    assigned_by UUID        REFERENCES users(id),
    assigned_at TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS role_assign_unique_idx
    ON role_assignments(user_id, role_key);
