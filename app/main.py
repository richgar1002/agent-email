"""Main FastAPI application - Agent Email Gateway"""
import os
import logging
from typing import Optional
from uuid import UUID

from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.db import models
from app.services.policy_service import PolicyService, PolicyDecision
from app.services.audit_service import AuditService
from app.services.safety_service import SafetyService
from app.services.transport_service import TransportService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Agent Email Gateway", version="1.0.0")

# Initialize services
transport_service = TransportService()
safety_service = SafetyService()


# === AUTH ===

def get_current_token(
    x_api_key: str = Header(None),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Authenticate using either x-api-key or Bearer token.
    Normalizes the auth approach.
    """
    token = None
    
    # Prefer x-api-key header
    if x_api_key:
        token = x_api_key
    # Also support Bearer token
    elif authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    
    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication")
    
    # Look up token in database
    import hashlib
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    api_token = db.query(models.ApiToken).filter(
        models.ApiToken.token_hash == token_hash,
        models.ApiToken.is_active == True
    ).first()
    
    if not api_token:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Update last used
    from datetime import datetime
    api_token.last_used_at = datetime.utcnow()
    db.commit()
    
    return api_token


# === SCHEMAS ===

class OrganizationCreate(BaseModel):
    name: str
    slug: str


class AgentCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None


class MailboxCreate(BaseModel):
    address: str
    provider_type: str = "smtp_imap"
    inbound_host: Optional[str] = None
    inbound_port: Optional[int] = None
    outbound_host: Optional[str] = None
    outbound_port: Optional[int] = None
    username: Optional[str] = None
    credential_ref: Optional[str] = None


class DraftGenerateRequest(BaseModel):
    message_id: str
    tone: str = "professional"
    context: Optional[str] = None


class DraftApproveRequest(BaseModel):
    decision: str  # approve, reject
    note: Optional[str] = None


# === HEALTH ===

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "1.0.0"
    }


# === ORGANIZATIONS ===

@app.post("/organizations")
def create_organization(
    request: OrganizationCreate,
    db: Session = Depends(get_db)
):
    """Create an organization"""
    org = models.Organization(
        name=request.name,
        slug=request.slug
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    
    return {"id": str(org.id), "name": org.name, "slug": org.slug}


@app.get("/organizations/{org_id}")
def get_organization(
    org_id: UUID,
    db: Session = Depends(get_db),
    token: models.ApiToken = Depends(get_current_token)
):
    """Get organization details"""
    if str(token.organization_id) != str(org_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return {"id": str(org.id), "name": org.name, "slug": org.slug}


# === AGENTS ===

@app.post("/organizations/{org_id}/agents")
def create_agent(
    org_id: UUID,
    request: AgentCreate,
    db: Session = Depends(get_db),
    token: models.ApiToken = Depends(get_current_token)
):
    """Create an agent"""
    if str(token.organization_id) != str(org_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    agent = models.Agent(
        organization_id=org_id,
        name=request.name,
        slug=request.slug,
        description=request.description
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    return {"id": str(agent.id), "name": agent.name, "slug": agent.slug}


@app.get("/organizations/{org_id}/agents/{agent_id}")
def get_agent(
    org_id: UUID,
    agent_id: UUID,
    db: Session = Depends(get_db),
    token: models.ApiToken = Depends(get_current_token)
):
    """Get agent details"""
    if str(token.organization_id) != str(org_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {
        "id": str(agent.id),
        "name": agent.name,
        "slug": agent.slug,
        "status": agent.status,
        "description": agent.description
    }


# === MAILBOXES ===

@app.post("/organizations/{org_id}/mailboxes")
def create_mailbox(
    org_id: UUID,
    request: MailboxCreate,
    db: Session = Depends(get_db),
    token: models.ApiToken = Depends(get_current_token)
):
    """Create a mailbox"""
    if str(token.organization_id) != str(org_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get agent from token or use provided
    agent_id = token.agent_id or db.query(models.Agent).filter(
        models.Agent.organization_id == org_id
    ).first().id
    
    mailbox = models.Mailbox(
        organization_id=org_id,
        agent_id=agent_id,
        address=request.address,
        provider_type=request.provider_type,
        inbound_host=request.inbound_host,
        inbound_port=request.inbound_port,
        outbound_host=request.outbound_host,
        outbound_port=request.outbound_port,
        username=request.username,
        credential_ref=request.credential_ref
    )
    db.add(mailbox)
    db.commit()
    db.refresh(mailbox)
    
    return {"id": str(mailbox.id), "address": mailbox.address}


@app.get("/organizations/{org_id}/mailboxes/{mailbox_id}")
def get_mailbox(
    org_id: UUID,
    mailbox_id: UUID,
    db: Session = Depends(get_db),
    token: models.ApiToken = Depends(get_current_token)
):
    """Get mailbox details"""
    if str(token.organization_id) != str(org_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    mailbox = db.query(models.Mailbox).filter(models.Mailbox.id == mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    
    return {
        "id": str(mailbox.id),
        "address": mailbox.address,
        "provider_type": mailbox.provider_type,
        "status": mailbox.status
    }


@app.get("/organizations/{org_id}/mailboxes/{mailbox_id}/messages")
def get_messages(
    org_id: UUID,
    mailbox_id: UUID,
    folder: str = "INBOX",
    limit: int = 10,
    unread_only: bool = False,
    db: Session = Depends(get_db),
    token: models.ApiToken = Depends(get_current_token)
):
    """Get messages from mailbox"""
    if str(token.organization_id) != str(org_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    mailbox = db.query(models.Mailbox).filter(models.Mailbox.id == mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    
    # Get transport and fetch
    transport = transport_service.get_transport(
        str(mailbox_id),
        {
            "provider_type": mailbox.provider_type,
            "imap_host": mailbox.inbound_host,
            "smtp_host": mailbox.outbound_host,
            "username": mailbox.username,
            "password": mailbox.credential_ref  # Would decrypt in production
        }
    )
    
    messages = transport.fetch_messages(folder, limit, unread_only)
    
    return {"messages": messages, "count": len(messages)}


@app.get("/organizations/{org_id}/mailboxes/{mailbox_id}/messages/{message_id}")
def get_message(
    org_id: UUID,
    mailbox_id: UUID,
    message_id: str,
    db: Session = Depends(get_db),
    token: models.ApiToken = Depends(get_current_token)
):
    """Get a specific message"""
    if str(token.organization_id) != str(org_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    mailbox = db.query(models.Mailbox).filter(models.Mailbox.id == mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    
    transport = transport_service.get_transport(
        str(mailbox_id),
        {
            "provider_type": mailbox.provider_type,
            "imap_host": mailbox.inbound_host,
            "smtp_host": mailbox.outbound_host,
            "username": mailbox.username,
            "password": mailbox.credential_ref
        }
    )
    
    message = transport.get_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Run safety scan
    safety_result = safety_service.scan_inbound_email(
        body_text=message.get("body", ""),
        from_addr=message.get("from")
    )
    
    return {
        **message,
        "safety_status": safety_result.status,
        "safety_risks": safety_result.risks
    }


# === DRAFTS ===

@app.post("/organizations/{org_id}/mailboxes/{mailbox_id}/drafts/generate")
def generate_draft(
    org_id: UUID,
    mailbox_id: UUID,
    request: DraftGenerateRequest,
    db: Session = Depends(get_db),
    token: models.ApiToken = Depends(get_current_token)
):
    """
    Generate a draft reply to a message.
    KEY CHANGE: Creates a draft, NOT a sent message.
    """
    if str(token.organization_id) != str(org_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    mailbox = db.query(models.Mailbox).filter(models.Mailbox.id == mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    
    # Get the original message
    transport = transport_service.get_transport(
        str(mailbox_id),
        {
            "provider_type": mailbox.provider_type,
            "imap_host": mailbox.inbound_host,
            "smtp_host": mailbox.outbound_host,
            "username": mailbox.username,
            "password": mailbox.credential_ref
        }
    )
    
    original_msg = transport.get_message(request.message_id)
    if not original_msg:
        raise HTTPException(status_code=404, detail="Original message not found")
    
    # Generate reply using LLM
    from enhanced_client import create_enhanced_email_client
    client = create_enhanced_email_client(
        hostname=mailbox.inbound_host or "imap.example.com",
        username=mailbox.username or "",
        password=mailbox.credential_ref or ""
    )
    
    result = client.generate_reply(
        original_subject=original_msg.get("subject", ""),
        original_body=original_msg.get("body", ""),
        from_addr=original_msg.get("from", ""),
        context=request.context,
        tone=request.tone
    )
    client.disconnect()
    
    # Create draft in database
    draft = models.Draft(
        organization_id=org_id,
        mailbox_id=mailbox_id,
        message_id=request.message_id,
        generated_by_agent_id=token.agent_id,
        to_addrs=[original_msg.get("from", "")],
        subject=f"Re: {original_msg.get('subject', '')}",
        body_text=result.get("reply", ""),
        confidence=result.get("confidence"),
        status="pending"
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    
    # Run policy check
    policy_service = PolicyService(db, str(org_id))
    
    # Check recipient (simplified)
    recipient = original_msg.get("from", "")
    policy_decision = policy_service.check_send_policy(draft, mailbox, recipient)
    
    # Update draft status based on policy
    if not policy_decision.allowed:
        draft.status = "needs_approval" if policy_decision.requires_approval else "rejected"
    else:
        draft.status = "pending"
    
    draft.policy_result = policy_decision.to_dict()
    db.commit()
    
    # Audit log
    audit = AuditService(db, str(org_id))
    audit.log_draft_created(str(draft.id), str(token.agent_id), str(mailbox_id))
    
    return {
        "draft_id": str(draft.id),
        "status": draft.status,
        "reply": result.get("reply"),
        "confidence": result.get("confidence"),
        "policy": policy_decision.to_dict()
    }


@app.post("/organizations/{org_id}/drafts/{draft_id}/approve")
def approve_draft(
    org_id: UUID,
    draft_id: UUID,
    request: DraftApproveRequest,
    db: Session = Depends(get_db),
    token: models.ApiToken = Depends(get_current_token)
):
    """Approve or reject a draft"""
    if str(token.organization_id) != str(org_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    draft = db.query(models.Draft).filter(models.Draft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    if request.decision == "approve":
        draft.status = "approved"
        draft.approved_at = __import__('datetime').datetime.utcnow()
        
        # Create approval record
        approval = models.Approval(
            draft_id=draft_id,
            requested_by_agent_id=draft.generated_by_agent_id,
            decision="approved",
            reviewer=token.agent_id,
            reviewer_note=request.note
        )
        db.add(approval)
        
        # Audit
        audit = AuditService(db, str(org_id))
        audit.log_draft_approved(str(draft_id), str(token.agent_id))
        
    elif request.decision == "reject":
        draft.status = "rejected"
        
        # Create approval record
        approval = models.Approval(
            draft_id=draft_id,
            requested_by_agent_id=draft.generated_by_agent_id,
            decision="rejected",
            reviewer=token.agent_id,
            reviewer_note=request.note
        )
        db.add(approval)
        
        # Audit
        audit = AuditService(db, str(org_id))
        audit.log_draft_rejected(str(draft_id), str(token.agent_id), request.note)
    
    db.commit()
    
    return {"draft_id": str(draft_id), "status": draft.status}


@app.post("/organizations/{org_id}/drafts/{draft_id}/send")
def send_draft(
    org_id: UUID,
    draft_id: UUID,
    db: Session = Depends(get_db),
    token: models.ApiToken = Depends(get_current_token)
):
    """Send an approved draft"""
    if str(token.organization_id) != str(org_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    draft = db.query(models.Draft).filter(models.Draft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    # Can only send approved drafts
    if draft.status != "approved":
        raise HTTPException(status_code=400, detail="Draft must be approved before sending")
    
    mailbox = db.query(models.Mailbox).filter(models.Mailbox.id == draft.mailbox_id).first()
    
    # Send via transport
    transport = transport_service.get_transport(
        str(mailbox.id),
        {
            "provider_type": mailbox.provider_type,
            "smtp_host": mailbox.outbound_host,
            "imap_host": mailbox.inbound_host,
            "username": mailbox.username,
            "password": mailbox.credential_ref
        }
    )
    
    success = transport.send_message(
        to_addrs=draft.to_addrs,
        subject=draft.subject,
        body=draft.body_text,
        from_addr=mailbox.address
    )
    
    if success:
        draft.status = "sent"
        from datetime import datetime
        draft.sent_at = datetime.utcnow()
        db.commit()
        
        # Audit
        audit = AuditService(db, str(org_id))
        audit.log_draft_sent(str(draft_id), str(token.agent_id), str(mailbox.id))
        
        return {"status": "sent", "draft_id": str(draft_id)}
    else:
        raise HTTPException(status_code=500, detail="Failed to send email")


@app.get("/organizations/{org_id}/drafts")
def list_drafts(
    org_id: UUID,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    token: models.ApiToken = Depends(get_current_token)
):
    """List drafts"""
    if str(token.organization_id) != str(org_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = db.query(models.Draft).filter(models.Draft.organization_id == org_id)
    
    if status:
        query = query.filter(models.Draft.status == status)
    
    drafts = query.order_by(models.Draft.created_at.desc()).limit(50).all()
    
    return {
        "drafts": [
            {
                "id": str(d.id),
                "subject": d.subject,
                "status": d.status,
                "confidence": d.confidence,
                "created_at": str(d.created_at)
            }
            for d in drafts
        ]
    }


# === WEBHOOKS ===

@app.post("/organizations/{org_id}/webhooks")
def create_webhook(
    org_id: str,
    name: str,
    target_url: str,
    trigger_type: str,
    trigger_value: str = "",
    auto_reply_enabled: bool = False,
    db: Session = Depends(get_db),
    token: models.ApiToken = Depends(get_current_token)
):
    """Create a webhook"""
    if str(token.organization_id) != str(org_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    webhook = models.Webhook(
        organization_id=org_id,
        agent_id=token.agent_id,
        name=name,
        target_url=target_url,
        trigger_type=trigger_type,
        trigger_value=trigger_value,
        auto_reply_enabled=auto_reply_enabled
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    
    return {"id": str(webhook.id), "name": webhook.name, "enabled": webhook.enabled}


@app.get("/organizations/{org_id}/webhooks")
def list_webhooks(
    org_id: UUID,
    db: Session = Depends(get_db),
    token: models.ApiToken = Depends(get_current_token)
):
    """List webhooks"""
    if str(token.organization_id) != str(org_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    webhooks = db.query(models.Webhook).filter(
        models.Webhook.organization_id == org_id
    ).all()
    
    return {
        "webhooks": [
            {
                "id": str(w.id),
                "name": w.name,
                "trigger_type": w.trigger_type,
                "enabled": w.enabled
            }
            for w in webhooks
        ]
    }


@app.delete("/organizations/{org_id}/webhooks/{webhook_id}")
def delete_webhook(
    org_id: UUID,
    webhook_id: UUID,
    db: Session = Depends(get_db),
    token: models.ApiToken = Depends(get_current_token)
):
    """Delete a webhook"""
    if str(token.organization_id) != str(org_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    webhook = db.query(models.Webhook).filter(
        models.Webhook.id == webhook_id,
        models.Webhook.organization_id == org_id
    ).first()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    db.delete(webhook)
    db.commit()
    
    return {"status": "deleted"}


# === AUDIT LOGS ===

@app.get("/organizations/{org_id}/audit")
def get_audit_logs(
    org_id: UUID,
    target_type: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    token: models.ApiToken = Depends(get_current_token)
):
    """Get audit logs"""
    if str(token.organization_id) != str(org_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    audit = AuditService(db, str(org_id))
    logs = audit.get_logs(target_type=target_type, limit=limit)
    
    return {
        "logs": [
            {
                "action": l.action,
                "target_type": l.target_type,
                "target_id": l.target_id,
                "status": l.status,
                "created_at": str(l.created_at)
            }
            for l in logs
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
