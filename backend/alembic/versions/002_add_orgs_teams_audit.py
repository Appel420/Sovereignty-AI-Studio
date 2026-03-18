"""Add orgs, teams, audit, usage, sessions, plugins tables

Revision ID: 002_add_orgs_teams_audit
Revises: 001_add_alerts
Create Date: 2026-03-18 06:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '002_add_orgs_teams_audit'
down_revision = '001_add_alerts'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── organizations ──────────────────────────────────────────────────────────
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('website', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('plan', sa.String(50), server_default='free', nullable=False),
        sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_organizations_slug', 'organizations', ['slug'])
    op.create_index('ix_organizations_name', 'organizations', ['name'])

    # ── org role enum ──────────────────────────────────────────────────────────
    op.execute("CREATE TYPE orgrole AS ENUM ('owner', 'admin', 'member', 'viewer')")

    # ── memberships ────────────────────────────────────────────────────────────
    op.create_table(
        'memberships',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('role', sa.Enum('owner', 'admin', 'member', 'viewer', name='orgrole'), nullable=False),
        sa.Column('invited_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('joined_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_memberships_org_id', 'memberships', ['organization_id'])
    op.create_index('ix_memberships_user_id', 'memberships', ['user_id'])

    # ── project role enum ──────────────────────────────────────────────────────
    op.execute("CREATE TYPE projectrole AS ENUM ('lead', 'contributor', 'viewer')")

    # ── org_projects ───────────────────────────────────────────────────────────
    op.create_table(
        'org_projects',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('project_type', sa.String(50), server_default='general', nullable=False),
        sa.Column('status', sa.String(50), server_default='active', nullable=False),
        sa.Column('is_archived', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_org_projects_organization_id', 'org_projects', ['organization_id'])

    # ── project_permissions ────────────────────────────────────────────────────
    op.create_table(
        'project_permissions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('org_projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('role', sa.Enum('lead', 'contributor', 'viewer', name='projectrole'), nullable=False),
        sa.Column('granted_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('granted_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_project_permissions_project_id', 'project_permissions', ['project_id'])
    op.create_index('ix_project_permissions_user_id', 'project_permissions', ['user_id'])

    # ── usage_records ──────────────────────────────────────────────────────────
    op.create_table(
        'usage_records',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=True),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), server_default='0', nullable=False),
        sa.Column('completion_tokens', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_tokens', sa.Integer(), server_default='0', nullable=False),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.Column('cost_usd', sa.Float(), server_default='0', nullable=False),
        sa.Column('status', sa.String(20), server_default='success', nullable=False),
        sa.Column('error_message', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_usage_records_user_id', 'usage_records', ['user_id'])
    op.create_index('ix_usage_records_provider', 'usage_records', ['provider'])
    op.create_index('ix_usage_records_created_at', 'usage_records', ['created_at'])

    # ── user_sessions ──────────────────────────────────────────────────────────
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('session_token', sa.String(255), unique=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('data', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_accessed_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_user_sessions_token', 'user_sessions', ['session_token'])
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'])

    # ── audit_logs ─────────────────────────────────────────────────────────────
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('actor_email', sa.String(255), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=True),
        sa.Column('resource_id', sa.String(100), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('status', sa.String(20), server_default='success', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_audit_logs_actor_id', 'audit_logs', ['actor_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])

    # ── plugins ────────────────────────────────────────────────────────────────
    op.create_table(
        'plugins',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), unique=True, nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('author', sa.String(255), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('entry_point', sa.String(500), nullable=False),
        sa.Column('config_schema', sa.JSON(), nullable=True),
        sa.Column('default_config', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(50), server_default='inactive', nullable=False),
        sa.Column('is_system', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('installed_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_health_check', sa.DateTime(), nullable=True),
        sa.Column('health_status', sa.String(50), nullable=True),
    )
    op.create_index('ix_plugins_name', 'plugins', ['name'])
    op.create_index('ix_plugins_status', 'plugins', ['status'])


def downgrade() -> None:
    op.drop_table('plugins')
    op.drop_table('audit_logs')
    op.drop_table('user_sessions')
    op.drop_table('usage_records')
    op.drop_table('project_permissions')
    op.drop_table('org_projects')
    op.drop_table('memberships')
    op.drop_table('organizations')
    op.execute('DROP TYPE IF EXISTS projectrole')
    op.execute('DROP TYPE IF EXISTS orgrole')
