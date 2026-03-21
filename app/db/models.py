"""Database models for Agent Email Platform"""
import uuid
import os
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, Numeric, JSON, ForeignKey, Index, DateTime
from sqlalchemy.orm import relationship

from app.db.session import Base


def generate_uuid():
    """Generate a UUID string"""
    return str(uuid.uuid4())


# All UUID fields use String(36) for cross-database compatibility
UUIDType = String(36)


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    name = Column(Text, nullable=False)
    slug = Column(Text, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    agents = relationship("Agent", back_populates="organization")
    mailboxes = relationship("Mailbox", back_populates="organization")
    threads = relationship("Thread", back_populates="organization")
    messages = relationship("Message", back_populates="organization")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    organization_id = Column(UUIDType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    slug = Column(Text, nullable=False)
    status = Column(Text, default="active")
    description = Column(Text)
    default_policy = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="agents")
    mailboxes = relationship("Mailbox", back_populates="agent")
    api_tokens = relationship("ApiToken", back_populates="agent")
    drafts = relationship("Draft", back_populates="generated_by_agent")


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    organization_id = Column(UUIDType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(UUIDType, ForeignKey("agents.id", ondelete="CASCADE"))
    token_hash = Column(Text, unique=True, nullable=False)
    name = Column(Text, nullable=False)
    scopes = Column(JSON, default=[])
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime)

    agent = relationship("Agent", back_populates="api_tokens")


class Mailbox(Base):
    __tablename__ = "mailboxes"

    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    organization_id = Column(UUIDType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(UUIDType, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    address = Column(Text, nullable=False)
    provider_type = Column(Text, nullable=False)
    inbound_host = Column(Text)
    inbound_port = Column(Integer)
    outbound_host = Column(Text)
    outbound_port = Column(Integer)
    username = Column(Text)
    credential_ref = Column(Text)
    status = Column(Text, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="mailboxes")
    agent = relationship("Agent", back_populates="mailboxes")
    threads = relationship("Thread", back_populates="mailbox")
    messages = relationship("Message", back_populates="mailbox")
    drafts = relationship("Draft", back_populates="mailbox")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    organization_id = Column(UUIDType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    email = Column(Text, nullable=False)
    display_name = Column(Text)
    trust_level = Column(Text, default="unknown")
    created_at = Column(DateTime, default=datetime.utcnow)


class Thread(Base):
    __tablename__ = "threads"

    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    organization_id = Column(UUIDType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    mailbox_id = Column(UUIDType, ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    provider_thread_id = Column(Text)
    subject = Column(Text)
    status = Column(Text, default="open")
    last_message_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="threads")
    mailbox = relationship("Mailbox", back_populates="threads")
    messages = relationship("Message", back_populates="thread")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    organization_id = Column(UUIDType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    mailbox_id = Column(UUIDType, ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    thread_id = Column(UUIDType, ForeignKey("threads.id", ondelete="SET NULL"))
    provider_message_id = Column(Text)
    direction = Column(Text, nullable=False)
    from_addr = Column(Text, nullable=False)
    to_addrs = Column(JSON, default=[])
    cc_addrs = Column(JSON, default=[])
    bcc_addrs = Column(JSON, default=[])
    subject = Column(Text)
    body_text = Column(Text)
    body_html = Column(Text)
    headers = Column(JSON, default={})
    received_at = Column(DateTime)
    sent_at = Column(DateTime)
    is_read = Column(Boolean, default=False)
    safety_status = Column(Text, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="messages")
    mailbox = relationship("Mailbox", back_populates="messages")
    thread = relationship("Thread", back_populates="messages")


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    message_id = Column(UUIDType, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    filename = Column(Text, nullable=False)
    content_type = Column(Text)
    size_bytes = Column(Integer)
    storage_key = Column(Text)
    scan_status = Column(Text, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class Webhook(Base):
    __tablename__ = "webhooks"

    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    organization_id = Column(UUIDType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(UUIDType, ForeignKey("agents.id", ondelete="CASCADE"))
    mailbox_id = Column(UUIDType, ForeignKey("mailboxes.id", ondelete="CASCADE"))
    name = Column(Text, nullable=False)
    target_url = Column(Text, nullable=False)
    trigger_type = Column(Text, nullable=False)
    trigger_value = Column(Text)
    headers = Column(JSON, default={})
    enabled = Column(Boolean, default=True)
    auto_reply_enabled = Column(Boolean, default=False)
    reply_template = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    runs = relationship("WebhookRun", back_populates="webhook")


class WebhookRun(Base):
    __tablename__ = "webhook_runs"

    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    webhook_id = Column(UUIDType, ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(UUIDType, ForeignKey("messages.id", ondelete="SET NULL"))
    event_type = Column(Text, nullable=False)
    success = Column(Boolean, default=False)
    response_code = Column(Integer)
    response_body = Column(Text)
    error_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    webhook = relationship("Webhook", back_populates="runs")


class Draft(Base):
    __tablename__ = "drafts"

    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    organization_id = Column(UUIDType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    mailbox_id = Column(UUIDType, ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    thread_id = Column(UUIDType, ForeignKey("threads.id", ondelete="SET NULL"))
    message_id = Column(UUIDType, ForeignKey("messages.id", ondelete="SET NULL"))
    generated_by_agent_id = Column(UUIDType, ForeignKey("agents.id", ondelete="SET NULL"))
    to_addrs = Column(JSON, default=[])
    cc_addrs = Column(JSON, default=[])
    bcc_addrs = Column(JSON, default=[])
    subject = Column(Text, nullable=False)
    body_text = Column(Text, nullable=False)
    status = Column(Text, default="pending")
    confidence = Column(Numeric(5, 4))
    policy_result = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime)
    sent_at = Column(DateTime)

    mailbox = relationship("Mailbox", back_populates="drafts")
    generated_by_agent = relationship("Agent", back_populates="drafts")


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    draft_id = Column(UUIDType, ForeignKey("drafts.id", ondelete="CASCADE"), nullable=False)
    requested_by_agent_id = Column(UUIDType, ForeignKey("agents.id", ondelete="SET NULL"))
    decision = Column(Text, default="pending")
    reviewer = Column(Text)
    reviewer_note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime)


class MemoryEvent(Base):
    __tablename__ = "memory_events"

    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    organization_id = Column(UUIDType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(UUIDType, ForeignKey("agents.id", ondelete="SET NULL"))
    mailbox_id = Column(UUIDType, ForeignKey("mailboxes.id", ondelete="SET NULL"))
    message_id = Column(UUIDType, ForeignKey("messages.id", ondelete="SET NULL"))
    memory_provider = Column(Text, nullable=False)
    external_memory_id = Column(Text)
    event_type = Column(Text, nullable=False)
    event_metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    organization_id = Column(UUIDType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(UUIDType, ForeignKey("agents.id", ondelete="SET NULL"))
    mailbox_id = Column(UUIDType, ForeignKey("mailboxes.id", ondelete="SET NULL"))
    action = Column(Text, nullable=False)
    target_type = Column(Text, nullable=False)
    target_id = Column(Text)
    status = Column(Text, nullable=False)
    audit_metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)


class Policy(Base):
    __tablename__ = "policies"

    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    organization_id = Column(UUIDType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    rule_type = Column(Text, nullable=False)
    condition = Column(JSON, default={})
    action = Column(Text, nullable=False)
    priority = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
