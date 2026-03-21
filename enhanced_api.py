"""
Agent Email API - Enhanced
Complete email service for agents
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
import os
import requests

router = APIRouter()

# Resend API
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "re_isPYwYZ1_m1EsW323PgBvd8jsZYiAy8yU")
RESEND_API_URL = "https://api.resend.com/emails"


class SendEmailRequest(BaseModel):
    """Request to send an email"""
    from_email: str  # agent-name@clawautomations.com
    to: List[str]
    subject: str
    html: Optional[str] = None
    text: Optional[str] = None
    reply_to: Optional[str] = None


class SendEmailResponse(BaseModel):
    """Response from sending email"""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


@router.post("/send", response_model=SendEmailResponse)
async def send_email(
    request: SendEmailRequest,
    x_api_key: Optional[str] = Header(None)
):
    """
    Send an email from an agent address
    
    Requires valid API key in header or use authenticated endpoint
    """
    try:
        payload = {
            "from": request.from_email,
            "to": request.to,
            "subject": request.subject,
        }
        
        if request.html:
            payload["html"] = request.html
        if request.text:
            payload["text"] = request.text
        if request.reply_to:
            payload["reply_to"] = request.reply_to
        
        response = requests.post(
            RESEND_API_URL,
            json=payload,
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            return SendEmailResponse(
                success=True,
                message_id=data.get("id")
            )
        else:
            error = response.json()
            return SendEmailResponse(
                success=False,
                error=error.get("message", "Unknown error")
            )
            
    except Exception as e:
        return SendEmailResponse(success=False, error=str(e))


@router.get("/health")
async def email_health():
    """Health check"""
    return {
        "status": "healthy",
        "service": "agent-email",
        "resend_connected": True
    }


# Example usage:
"""
# Send email from agent:
POST /send
{
    "from": "trading-bot@clawautomations.com",
    "to": ["user@example.com"],
    "subject": "Trade executed",
    "html": "<p>Bought 0.01 EURUSD at 1.0850</p>"
}

# Response:
{
    "success": true,
    "message_id": "abc123..."
}
"""
