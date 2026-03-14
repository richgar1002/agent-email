# 🕵️ AgentMail Decentralized

**Privacy-first email for AI agents. Self-hosted. No cloud.**

---

## The Problem

| Cloud Email Services | The Decentralized Solution |
|---------------------|--------------------------|
| Your data on their servers | Data stays on your VPS |
| Monthly subscription | One VPS cost |
| Privacy concerns | Complete data sovereignty |
| Vendor lock-in | Full control |
| Rate limits | Your server, your rules |

## Why Decentralized?

### 🔒 Privacy
- Emails never leave your infrastructure
- No third-party data processing
- GDPR/HIPAA compliant by design

### 💰 Cost
- No per-email pricing
- One VPS = unlimited inboxes
- For power users: much cheaper than cloud

### 🛡️ Control
- Full server control
- Custom configurations
- No downtime due to vendor issues

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
    "smtp_host": "mail.yourdomain.com"
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

## Python SDK

```python
from client import create_email_client

# Connect
email = create_email_client(
    hostname="mail.yourdomain.com",
    username="trading-bot@yourdomain.com",
    password="secure-password"
)

# Get messages
messages = email.get_messages(limit=10)
for msg in messages:
    print(f"From: {msg.from_addr}")
    print(f"Subject: {msg.subject}")
    print(f"Body: {msg.body[:100]}...")

# Send email
email.send(
    to_addr="client@example.com",
    subject="Trading Update",
    body="EURUSD closed at 1.0850 (+$45.20)"
)
```

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
│           ┌───────▼───────┐                    │
│           │   Your Agent  │                    │
│           │   (Browser,   │                    │
│           │   Memory)     │                    │
│           └───────────────┘                    │
│                                                  │
└─────────────────────────────────────────────────┘
```

## Docker Deployment (Coming Soon)

```yaml
# docker-compose.yml
version: '3'
services:
  email-api:
    image: agent-email
    ports:
      - "8002:8002"
    env_file:
      - .env
```

## Features

### Core
- IMAP/SMTP support
- REST API
- Multiple accounts
- Attachments

### AI Integration
- Send/receive via API
- Agent SDK
- Memory integration (coming)
- Auto-reply with LLM (coming)

### Security
- API key auth
- TLS encryption
- DKIM ready
- Full audit logs (coming)

## Pricing

| Model | Price | Who |
|-------|-------|-----|
| **Open Source** | $0 | Self-hosters |
| **Managed Install** | $99 one-time | Want help |
| **VPS + Support** | $15/mo | Fully managed |

## Status

**MVP Ready** ✅

Features implemented:
- ✅ IMAP client
- ✅ SMTP client
- ✅ REST API
- ✅ Python SDK
- ✅ Multiple accounts
- ✅ Send/receive emails

Coming soon:
- 🔄 Webhooks
- 🔄 DKIM signing
- 🔄 Spam filtering
- 🔄 Memory integration
- 🔄 LLM auto-reply

## License

MIT
