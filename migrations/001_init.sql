-- Agent Email Platform v1 Schema
-- Refactored from prototype to agent control plane

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Organizations (multi-tenant support)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Agents (agent identity + permissions)
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active', -- active, paused, deleted
    description TEXT,
    default_policy JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, slug)
);

-- API Tokens (scoped credentials)
CREATE TABLE api_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ
);

-- Mailboxes (email accounts per agent)
CREATE TABLE mailboxes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    address TEXT NOT NULL,
    provider_type TEXT NOT NULL, -- smtp_imap, gmail, graph
    inbound_host TEXT,
    inbound_port INT,
    outbound_host TEXT,
    outbound_port INT,
    username TEXT,
    credential_ref TEXT, -- encrypted secret ref or vault key
    status TEXT NOT NULL DEFAULT 'active', -- active, inactive, error
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, address)
);

-- Contacts (address book with trust levels)
CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    display_name TEXT,
    trust_level TEXT NOT NULL DEFAULT 'unknown', -- trusted, internal, external, blocked, unknown
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, email)
);

-- Threads (conversation threads)
CREATE TABLE threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    mailbox_id UUID NOT NULL REFERENCES mailboxes(id) ON DELETE CASCADE,
    provider_thread_id TEXT,
    subject TEXT,
    status TEXT NOT NULL DEFAULT 'open', -- open, closed, archived
    last_message_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Messages (normalized email)
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    mailbox_id UUID NOT NULL REFERENCES mailboxes(id) ON DELETE CASCADE,
    thread_id UUID REFERENCES threads(id) ON DELETE SET NULL,
    provider_message_id TEXT,
    direction TEXT NOT NULL, -- inbound, outbound
    from_addr TEXT NOT NULL,
    to_addrs JSONB NOT NULL DEFAULT '[]'::jsonb,
    cc_addrs JSONB NOT NULL DEFAULT '[]'::jsonb,
    bcc_addrs JSONB NOT NULL DEFAULT '[]'::jsonb,
    subject TEXT,
    body_text TEXT,
    body_html TEXT,
    headers JSONB NOT NULL DEFAULT '{}'::jsonb,
    received_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    safety_status TEXT NOT NULL DEFAULT 'pending', -- pending, safe, suspicious, blocked
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for common queries
CREATE INDEX idx_messages_mailbox_received_at ON messages(mailbox_id, received_at DESC);
CREATE INDEX idx_messages_thread_id ON messages(thread_id);
CREATE INDEX idx_messages_provider_message_id ON messages(provider_message_id);

-- Attachments
CREATE TABLE attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    content_type TEXT,
    size_bytes BIGINT,
    storage_key TEXT,
    scan_status TEXT NOT NULL DEFAULT 'pending', -- pending, safe, suspicious, blocked
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Webhooks
CREATE TABLE webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    mailbox_id UUID REFERENCES mailboxes(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    target_url TEXT NOT NULL,
    trigger_type TEXT NOT NULL, -- new_email, from_address, subject_matches, body_contains, attachment
    trigger_value TEXT,
    headers JSONB NOT NULL DEFAULT '{}'::jsonb,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    auto_reply_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    reply_template TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Webhook execution logs
CREATE TABLE webhook_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    webhook_id UUID NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    success BOOLEAN NOT NULL DEFAULT FALSE,
    response_code INT,
    response_body TEXT,
    error_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Drafts (approval workflow)
CREATE TABLE drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    mailbox_id UUID NOT NULL REFERENCES mailboxes(id) ON DELETE CASCADE,
    thread_id UUID REFERENCES threads(id) ON DELETE SET NULL,
    message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    generated_by_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    to_addrs JSONB NOT NULL DEFAULT '[]'::jsonb,
    cc_addrs JSONB NOT NULL DEFAULT '[]'::jsonb,
    bcc_addrs JSONB NOT NULL DEFAULT '[]'::jsonb,
    subject TEXT NOT NULL,
    body_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- pending, needs_approval, approved, rejected, sent
    confidence NUMERIC(5,4),
    policy_result JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ
);

-- Approvals (human-in-the-loop)
CREATE TABLE approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id UUID NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
    requested_by_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    decision TEXT NOT NULL DEFAULT 'pending', -- pending, approved, rejected
    reviewer TEXT,
    reviewer_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at TIMESTAMPTZ
);

-- Memory events (track what's saved to external memory)
CREATE TABLE memory_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    mailbox_id UUID REFERENCES mailboxes(id) ON DELETE SET NULL,
    message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    memory_provider TEXT NOT NULL, -- supabase, sqlite, etc
    external_memory_id TEXT,
    event_type TEXT NOT NULL, -- saved, updated, failed
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Audit logs (everything that happens)
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    mailbox_id UUID REFERENCES mailboxes(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT,
    status TEXT NOT NULL, -- success, failure
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Policy rules
CREATE TABLE policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    rule_type TEXT NOT NULL, -- external_requires_approval, attachment_requires_approval, low_confidence_requires_approval, trusted_sender_overrides, blocked_sender_blocked, financial_blocked
    condition JSONB NOT NULL DEFAULT '{}'::jsonb,
    action TEXT NOT NULL, -- approve, block, require_approval
    priority INT NOT NULL DEFAULT 0,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
