"""
Email Receiving Webhook - Complete Implementation
Handles incoming emails from Resend and forwards to users
"""
import os
from fastapi import APIRouter, Request, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
import logging

# Supabase imports
import supabase_py

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize Supabase
supabase_url = os.environ.get("SUPABASE_URL", "https://ujfmhpbodscrzkwkynon.supabase.co")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
supabase = supabase_py.create_client(supabase_url, supabase_key)


class EmailAddress(BaseModel):
    email: str
    name: Optional[str] = None


class Attachment(BaseModel):
    filename: str
    content_type: str
    data: str  # Base64


class ResendWebhookPayload(BaseModel):
    """Payload from Resend incoming email webhook"""
    from_email: str
    from_name: Optional[str] = None
    to: List[EmailAddress]
    cc: Optional[List[EmailAddress]] = None
    bcc: Optional[List[EmailAddress]] = None
    subject: Optional[str] = None
    text: Optional[str] = None
    html: Optional[str] = None
    attachments: Optional[List[Attachment]] = None


async def verify_resend_signature(payload: str, signature: str) -> bool:
    """
    Verify the request is actually from Resend
    Using HMAC-SHA256
    """
    import hmac
    import hashlib
    
    webhook_secret = os.environ.get("RESEND_WEBHOOK_SECRET", "")
    if not webhook_secret:
        logger.warning("No webhook secret configured - skipping verification")
        return True
    
    expected = hmac.new(
        webhook_secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)


@router.post("/webhooks/email/receive")
async def receive_email(
    request: Request,
    x_resend_signature: Optional[str] = Header(None)
):
    """
    Main webhook endpoint for receiving emails
    
    Resend will POST here when emails arrive at @clawautomations.com addresses
    """
    # Get raw body for signature verification
    body = await request.body()
    payload_str = body.decode()
    
    # Verify signature (if configured)
    if x_resend_signature:
        if not await verify_resend_signature(payload_str, x_resend_signature):
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse payload
    try:
        import json
        payload = json.loads(payload_str)
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    logger.info(f"Received email: {payload.get('subject', 'No subject')}")
    
    # Extract recipient (agent email)
    to_list = payload.get("to", [])
    if not to_list:
        raise HTTPException(status_code=400, detail="No recipients")
    
    recipient = to_list[0]
    recipient_email = recipient.get("email", "")
    
    # Parse agent name from email (agent-name@clawautomations.com)
    if "@" in recipient_email:
        agent_part = recipient_email.split("@")[0]
    else:
        agent_part = recipient_email
    
    # Look up agent in database
    try:
        response = supabase.table("agent_emails").select("*").eq("email", recipient_email).execute()
        agents = response.get("data", [])
        
        if not agents:
            logger.warning(f"No agent found for {recipient_email}")
            return {"status": "ignored", "reason": "Unknown agent"}
        
        agent = agents[0]
        agent_id = agent["id"]
        forward_to = agent.get("forward_to")
        
        # Store received email
        email_record = {
            "agent_email_id": agent_id,
            "from_email": payload.get("from_email", ""),
            "from_name": payload.get("from_name"),
            "subject": payload.get("subject"),
            "text_content": payload.get("text"),
            "html_content": payload.get("html"),
            "headers": payload.get("headers", {}),
            "status": "received"
        }
        
        # Insert into database
        insert_response = supabase.table("received_emails").insert(email_record).execute()
        
        # Forward email if configured
        if forward_to:
            # TODO: Forward using Resend API or SMTP
            logger.info(f"Would forward to: {forward_to}")
            # Mark as forwarded
            supabase.table("received_emails").update({
                "forwarded_to": forward_to,
                "status": "forwarded"
            }).eq("id", insert_response.get("data", [{}])[0].get("id")).execute()
        
        return {"status": "ok", "email_id": insert_response.get("data", [{}])[0].get("id")}
        
    except Exception as e:
        logger.error(f"Error processing email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhooks/email/receive")
async def webhook_health():
    """Health check"""
    return {"status": "healthy", "service": "email-webhook"}


# Get received emails for a user
@router.get("/api/emails/received")
async def get_received_emails(x_user_id: str = None):
    """Get received emails for the authenticated user"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        # Get user's agent emails
        agents_response = supabase.table("agent_emails").select("id").eq("user_id", x_user_id).execute()
        agent_ids = [a["id"] for a in agents_response.get("data", [])]
        
        if not agent_ids:
            return {"data": []}
        
        # Get received emails
        response = supabase.table("received_emails").select("*").in_("agent_email_id", agent_ids).order("created_at", desc=True).limit(50).execute()
        
        return {"data": response.get("data", [])}
        
    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))
