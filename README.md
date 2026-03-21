# Agent Email Platform

## Quick Start

### 1. Run Migration

```bash
psql $DATABASE_URL -f migrations/001_init.sql
```

### 2. Set Environment

```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/agent_email"
export API_KEY="your-api-key"
```

### 3. Run the Server

```bash
python -m app.main
```

## Architecture

```
agent-email/
├── app/
│   ├── main.py              # FastAPI application
│   ├── db/
│   │   ├── session.py       # Database connection
│   │   └── models.py        # SQLAlchemy models
│   ├── services/
│   │   ├── policy_service.py   # Approval rules
│   │   ├── audit_service.py    # Action logging
│   │   ├── safety_service.py   # Inbound email safety
│   │   └── transport_service.py # Email providers
│   └── api/                 # Route handlers
├── migrations/
│   └── 001_init.sql        # v1 schema
└── README.md
```

## Key Changes from Prototype

### Old → New Mapping

| Old File | New Location |
|----------|-------------|
| `enhanced_client.py` | `app/services/transport_service.py` |
| `memory_integration.py` | `app/providers/memory/` |
| `webhook_manager.py` | `app/services/webhook_service.py` |
| `llm_reply.py` | `app/services/reply_service.py` |
| `api.py` | `app/main.py` |
| In-memory `accounts` dict | `mailboxes` table |
| File-based webhooks | `webhooks` table |
| Direct send | `drafts` + `approvals` tables |

## API Overview

### Organizations
- `POST /organizations` - Create org
- `GET /organizations/{id}` - Get org

### Agents
- `POST /organizations/{org_id}/agents` - Create agent
- `GET /organizations/{org_id}/agents/{id}` - Get agent

### Mailboxes
- `POST /organizations/{org_id}/mailboxes` - Add mailbox
- `GET /organizations/{org_id}/mailboxes/{id}/messages` - List messages

### Drafting (NEW - draft-by-default)
- `POST .../mailboxes/{id}/drafts/generate` - Generate reply draft
- `POST .../drafts/{id}/approve` - Approve draft
- `POST .../drafts/{id}/reject` - Reject draft
- `POST .../drafts/{id}/send` - Send approved draft

### Webhooks
- `POST /organizations/{org_id}/webhooks` - Create webhook
- `GET /organizations/{org_id}/webhooks` - List webhooks

### Audit
- `GET /organizations/{org_id}/audit` - View action logs

## Policy Rules (v1)

Default hardcoded rules:
1. **External recipients** → require approval
2. **Low confidence (<0.7)** → require approval
3. **Blocked senders** → blocked
4. **Trusted senders** → auto-approved

Custom policies can be added via the `policies` table.

## Safety

Inbound email is treated as hostile. The `SafetyService`:
- Sanitizes HTML/scripts
- Extracts and flags links
- Quarantines dangerous attachments
- Detects tool instruction attempts

## Auth

Supports both:
- `x-api-key` header
- `Authorization: Bearer <token>` header

Tokens are stored as SHA256 hashes in the `api_tokens` table with scoped permissions.
