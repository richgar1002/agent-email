# 🕵️ AgentMail Decentralized

**Privacy-first email for AI agents. Self-hosted. No cloud.**

---

## Beta Features

| Feature | Status |
|---------|--------|
| IMAP/SMTP | ✅ |
| REST API | ✅ |
| Multiple accounts | ✅ |
| Send/receive | ✅ |
| **Memory Integration** | ✅ NEW |
| **Webhooks** | ✅ NEW |
| **LLM Auto-Reply** | ✅ NEW |

---

## The Problem

| Cloud Email Services | The Decentralized Solution |
|---------------------|--------------------------|
| Your data on their servers | Data stays on your VPS |
| Monthly subscription | One VPS cost |
| Privacy concerns | Complete data sovereignty |
| Vendor lock-in | Full control |
| Rate limits | Your server, your rules |

---

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Run API
python api.py
```

## Configuration

```env
# .env file
API_KEY=your-secret-key
SMTP_HOST=mail.yourdomain.com
IMAP_HOST=mail.yourdomain.com
DEFAULT_DOMAIN=yourdomain.com
```

## API Usage

### Create Account
```bash
curl -X POST http://localhost:8002/accounts \
  -H "Authorization: Bearer YOUR-API-KEY" \
  -d '{
    "username": "trading-bot",
    "password": "secure-password",
    "smtp_host": "live.smtp.mailtrap.io",
    "imap_host": "live.imap.mailtrap.io"
  }'
```

### Get Messages
```bash
curl http://localhost:8002/accounts/trading-bot/messages \
  -H "Authorization: Bearer YOUR-API-KEY"
```

### Send Email
```bash
curl -X POST http://localhost:8002/accounts/trading-bot/send \
  -H "Authorization: Bearer YOUR-API-KEY" \
  -d '{
    "to_addr": "client@example.com",
    "subject": "Update",
    "body": "Your trade closed at profit."
  }'
```

## New: Memory Integration

Save emails to memory bridge:

```bash
# Save email to memory
curl -X POST http://localhost:8002/accounts/trading-bot/memory/save \
  -H "Authorization: Bearer YOUR-API-KEY" \
  -d '{"msg_id": "123"}'

# Search saved emails
curl "http://localhost:8002/accounts/trading-bot/memory/search?query=trading" \
  -H "Authorization: Bearer YOUR-API-KEY"
```

## New: Webhooks

Trigger actions on incoming emails:

```bash
# Create webhook
curl -X POST http://localhost:8002/accounts/trading-bot/webhooks \
  -H "Authorization: Bearer YOUR-API-KEY" \
  -d '{
    "name": "Trade Alerts",
    "url": "https://your-server.com/webhook",
    "trigger_type": "subject_matches",
    "trigger_value": "trade"
  }'
```

### Trigger Types
- `new_email` - Any new email
- `from_address` - From specific address
- `subject_matches` - Subject contains text
- `body_contains` - Body contains text

## New: LLM Auto-Reply

AI-powered email responses:

```bash
# Generate reply
curl -X POST http://localhost:8002/accounts/trading-bot/reply/generate \
  -H "Authorization: Bearer YOUR-API-KEY" \
  -d '{
    "from_addr": "client@example.com",
    "subject": "Question about trading",
    "body": "What are the best pairs for scalping?",
    "tone": "professional"
  }'

# Send auto-reply
curl -X POST http://localhost:8002/accounts/trading-bot/reply/auto/123 \
  -H "Authorization: Bearer YOUR-API-KEY" \
  -d '{"tone": "professional"}'
```

### Tones
- `professional` - Formal business style
- `casual` - Friendly, relaxed
- `brief` - Short and to the point

## Python SDK

```python
from enhanced_client import create_enhanced_email_client

# Connect
email = create_enhanced_email_client(
    hostname="mail.yourdomain.com",
    username="trading-bot@yourdomain.com",
    password="secure-password",
    user_id="trading"
)

# Get messages
messages = email.get_messages(limit=10)

# Save to memory
email.save_to_memory(msg_id="123")

# Generate AI reply
result = email.generate_reply(
    original_subject="Question",
    original_body="What's the best strategy?",
    from_addr="client@example.com",
    tone="professional"
)
print(result['reply'])

# Send auto-reply
email.send_auto_reply(msg_id="123", tone="professional")

# Summarize email
summary = email.summarize_email(msg_id="123")
print(summary)
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/accounts` | Create account |
| GET | `/accounts/{id}` | Get account |
| GET | `/accounts/{id}/messages` | List messages |
| POST | `/accounts/{id}/send` | Send email |
| POST | `/accounts/{id}/memory/save` | Save to memory |
| GET | `/accounts/{id}/memory/search` | Search memory |
| POST | `/accounts/{id}/reply/generate` | Generate reply |
| POST | `/accounts/{id}/reply/auto` | Send auto-reply |
| GET | `/accounts/{id}/summarize/{msg_id}` | Summarize |
| POST | `/accounts/{id}/webhooks` | Create webhook |
| GET | `/accounts/{id}/webhooks` | List webhooks |

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Your VPS (Self-Hosted)             │
├─────────────────────────────────────────────────┤
│                                                  │
│   ┌──────────────┐    ┌──────────────┐       │
│   │   SMTP Server │    │  IMAP Server │       │
│   │   (outbound)  │    │  (inbound)   │       │
│   └───────┬───────┘    └───────┬───────┘       │
│           │                    │                │
│           └────────┬───────────┘                │
│                    ▼                            │
│           ┌───────────────┐                    │
│           │  REST API     │                    │
│           │  (port 8002)  │                    │
│           └───────┬───────┘                    │
│                   │                            │
│    ┌──────────────┼──────────────┐            │
│    ▼              ▼              ▼            │
│ ┌──────┐   ┌──────────┐   ┌──────────┐     │
│ │Memory│◀──│  Webhooks │──▶│   LLM    │     │
│ │Bridge│   │           │   │  Auto-   │     │
│ └──────┘   └──────────┘   │  Reply   │     │
│                             └──────────┘     │
└─────────────────────────────────────────────────┘
```

---

## Status

**Beta Ready** ✅

Features implemented:
- ✅ IMAP client
- ✅ SMTP client
- ✅ REST API
- ✅ Python SDK
- ✅ Multiple accounts
- ✅ Send/receive emails
- ✅ Memory integration
- ✅ Webhooks
- ✅ LLM auto-reply

---

**License:** MIT
