# Agent Email - TODO List

## Phase 1: Core Infrastructure (MVP)

### Email Sending ✅
- [x] SMTP integration with Resend
- [x] Send emails via API
- [ ] Custom domain (@clawautomations.com) - DNS pending

### Email Receiving
- [x] Webhook endpoint structure
- [x] Parse incoming emails
- [ ] Set up catch-all in Resend (needs domain verified)
- [ ] Forward to user's configured address
- [ ] Store in database

### Agent Integration
- [x] API endpoint for agents to send emails
- [x] Authentication via API key
- [ ] Rate limiting per agent

---

## Phase 2: Features

### Email Management
- [x] List agent email addresses per user
- [x] Update forwarding addresses
- [ ] Delete agent emails
- [ ] Email templates

### AI Features
- [x] AI reply generation
- [x] Auto-responder rules
- [x] Email summarization
- [x] Intent classification

### Webhooks
- [ ] Webhook triggers (new email, reply received)
- [ ] Webhook management UI

---

## Phase 3: Production

### Deliverability
- [ ] SPF/DKIM/DMARC verification
- [ ] Email bounce handling
- [ ] Email open tracking
- [ ] Reply tracking

### Multi-tenancy
- [ ] Per-customer email routing
- [ ] Custom domains per customer
- [ ] Sender verification

### Dashboard
- [ ] View sent emails
- [ ] View received emails
- [ ] Email activity stats
- [ ] Webhook logs

---

## Phase 4: Advanced

### Automation
- [ ] Email-based triggers
- [ ] Agent-to-agent email
- [ ] Scheduled emails
- [ ] Email templates library

### Integrations
- [ ] Slack notifications
- [ ] Discord webhooks
- [ ] Notion integration
- [ ] Calendar sync

---

## Technical Debt
- [ ] Error handling improvements
- [ ] Logging & monitoring
- [ ] Unit tests
- [ ] API documentation (OpenAPI/Swagger)
