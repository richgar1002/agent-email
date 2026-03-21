"""Audit Service - logs all actions"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import uuid

from app.db.models import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """
    Audit logging for compliance and debugging
    """
    
    def __init__(self, db: Session, organization_id: str):
        self.db = db
        self.organization_id = organization_id
    
    def log(
        self,
        action: str,
        target_type: str,
        target_id: Optional[str] = None,
        status: str = "success",
        agent_id: Optional[str] = None,
        mailbox_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log an action"""
        
        log_entry = AuditLog(
            id=uuid.uuid4(),
            organization_id=self.organization_id,
            agent_id=agent_id,
            mailbox_id=mailbox_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            status=status,
            audit_metadata=metadata or {},
            created_at=datetime.utcnow()
        )
        
        self.db.add(log_entry)
        self.db.commit()
        
        logger.info(f"AUDIT: {action} on {target_type}:{target_id} - {status}")
    
    def log_draft_created(self, draft_id: str, agent_id: str, mailbox_id: str, metadata: Dict = None):
        self.log(
            action="draft.created",
            target_type="draft",
            target_id=draft_id,
            agent_id=agent_id,
            mailbox_id=mailbox_id,
            metadata=metadata
        )
    
    def log_draft_approved(self, draft_id: str, reviewer: str, agent_id: str = None):
        self.log(
            action="draft.approved",
            target_type="draft",
            target_id=draft_id,
            agent_id=agent_id,
            metadata={"reviewer": reviewer}
        )
    
    def log_draft_rejected(self, draft_id: str, reviewer: str, note: str = None):
        self.log(
            action="draft.rejected",
            target_type="draft",
            target_id=draft_id,
            status="failure" if note else "success",
            metadata={"reviewer": reviewer, "note": note}
        )
    
    def log_draft_sent(self, draft_id: str, agent_id: str, mailbox_id: str):
        self.log(
            action="draft.sent",
            target_type="draft",
            target_id=draft_id,
            agent_id=agent_id,
            mailbox_id=mailbox_id,
            status="success"
        )
    
    def log_message_received(self, message_id: str, mailbox_id: str, from_addr: str):
        self.log(
            action="message.received",
            target_type="message",
            target_id=message_id,
            mailbox_id=mailbox_id,
            metadata={"from": from_addr}
        )
    
    def log_webhook_fired(self, webhook_id: str, message_id: str = None, success: bool = True):
        self.log(
            action="webhook.fired",
            target_type="webhook",
            target_id=webhook_id,
            status="success" if success else "failure",
            metadata={"message_id": str(message_id) if message_id else None}
        )
    
    def log_memory_saved(self, message_id: str, memory_id: str, provider: str):
        self.log(
            action="memory.saved",
            target_type="message",
            target_id=message_id,
            metadata={"memory_id": memory_id, "provider": provider}
        )
    
    def log_error(self, action: str, target_type: str, error: str, metadata: Dict = None):
        self.log(
            action=action,
            target_type=target_type,
            status="failure",
            metadata={**(metadata or {}), "error": error}
        )
    
    def get_logs(
        self,
        agent_id: str = None,
        mailbox_id: str = None,
        target_type: str = None,
        limit: int = 100
    ) -> list:
        """Query audit logs"""
        
        query = self.db.query(AuditLog).filter(
            AuditLog.organization_id == self.organization_id
        )
        
        if agent_id:
            query = query.filter(AuditLog.agent_id == agent_id)
        
        if mailbox_id:
            query = query.filter(AuditLog.mailbox_id == mailbox_id)
        
        if target_type:
            query = query.filter(AuditLog.target_type == target_type)
        
        return query.order_by(AuditLog.created_at.desc()).limit(limit).all()
