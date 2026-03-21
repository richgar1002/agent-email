"""
Email Receiving Webhook
Handles incoming emails from Resend

When domain is verified:
1. Set up catch-all route in Resend dashboard
2. Point to this webhook endpoint
3. Parse email and forward to user
"""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


class EmailRecipient(BaseModel):
    """Recipient of the email"""
    email: str
    name: Optional[str] = None


class EmailAttachment(BaseModel):
    """Email attachment"""
    filename: str
    content_type: str
    data: str  # Base64 encoded


class IncomingEmail(BaseModel):
    """Incoming email payload from Resend"""
    from_email: str
    from_name: Optional[str] = None
    to: List[EmailRecipient]
    cc: Optional[List[EmailRecipient]] = None
    bcc: Optional[List[EmailRecipient]] = None
    subject: Optional[str] = None
    text: Optional[str] = None
    html: Optional[str] = None
    attachments: Optional[List[EmailAttachment]] = None


@router.post("/webhook/email/receive")
async def receive_email(payload: IncomingEmail):
    """
    Receive incoming email from Resend
    
    Payload contains:
    - from: sender email
    - to: list of recipients
    - subject: email subject
    - text: plain text body
    - html: HTML body
    - attachments: any files
    """
    logger.info(f"Received email: {payload.subject} from {payload.from_email}")
    
    # Extract agent email (to address)
    if payload.to:
        recipient_email = payload.to[0].email
        agent_name = recipient_email.split('@')[0] if '@' in recipient_email else None
    else:
        raise HTTPException(status_code=400, detail="No recipients found")
    
    # Parse sender
    sender_email = payload.from_email
    
    # Store email in database
    # TODO: Add to Supabase
    
    # Forward to user's configured address
    # TODO: Look up forwarding address from database
    
    logger.info(f"Email for agent: {agent_name}")
    
    return {
        "status": "received",
        "agent": agent_name,
        "from": sender_email,
        "subject": payload.subject
    }


@router.get("/webhook/email/receive")
async def receive_email_get():
    """Health check for webhook"""
    return {"status": "ok", "service": "email-receive-webhook"}


# Resend webhook verification (for initial setup)
@router.get("/webhook/email/verify")
async def verify_webhook(request: Request):
    """
    Resend will call this to verify the webhook endpoint
    """
    # Return 200 OK for verification
    return {"status": "verified"}
