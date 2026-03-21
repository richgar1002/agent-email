"""
Enhanced Email API
Complete REST API with memory, webhooks, and LLM
"""
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os

from enhanced_client import EnhancedEmailClient, create_enhanced_email_client
from webhook_manager import EmailTrigger

app = FastAPI(title="Agent Email API - Enhanced")

# Config
SMTP_HOST = os.getenv("SMTP_HOST", "live.smtp.mailtrap.io")
IMAP_HOST = os.getenv("IMAP_HOST", "live.imap.mailtrap.io")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))

# Storage
DATA_DIR = "/tmp/email_data"
os.makedirs(DATA_DIR, exist_ok=True)

# Simple in-memory storage for multiple accounts
accounts = {}

def verify_api_key(x_api_key: str = Header(None)):
    """Verify API key"""
    expected = os.getenv("API_KEY", "secret")
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

# Models

class CreateAccountRequest(BaseModel):
    username: str
    password: str
    smtp_host: Optional[str] = None
    imap_host: Optional[str] = None
    smtp_port: Optional[int] = 587
    imap_port: Optional[int] = 993
    user_id: Optional[str] = None

class SendEmailRequest(BaseModel):
    from_addr: Optional[str] = None
    to_addr: str
    subject: str
    body: str
    html: bool = False

class WebhookRequest(BaseModel):
    name: str
    url: str
    trigger_type: str
    trigger_value: str
    auto_reply: bool = False
    reply_template: Optional[str] = None

class AutoReplyRequest(BaseModel):
    tone: str = "professional"
    context: Optional[str] = None

class GenerateReplyRequest(BaseModel):
    from_addr: str
    subject: str
    body: str
    tone: str = "professional"
    context: Optional[str] = None

# === ACCOUNTS ===

@app.post("/accounts")
async def create_account(
    request: CreateAccountRequest,
    auth: bool = Depends(verify_api_key)
):
    """Create an email account"""
    account_id = request.username
    
    accounts[account_id] = {
        "username": request.username,
        "password": request.password,
        "smtp_host": request.smtp_host or SMTP_HOST,
        "imap_host": request.imap_host or IMAP_HOST,
        "smtp_port": request.smtp_port,
        "imap_port": request.imap_port,
        "user_id": request.user_id or request.username,
        "created_at": datetime.now().isoformat()
    }
    
    return {
        "account_id": account_id,
        "address": f"{request.username}@{request.smtp_host or SMTP_HOST}"
    }

@app.get("/accounts/{account_id}")
async def get_account(
    account_id: str,
    auth: bool = Depends(verify_api_key)
):
    """Get account info"""
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = accounts[account_id]
    
    try:
        client = create_enhanced_email_client(
            hostname=account["imap_host"],
            username=account["username"],
            password=account["password"],
            user_id=account.get("user_id"),
            storage_path=DATA_DIR
        )
        
        inbox = client.get_inbox()
        client.disconnect()
        
        return {
            "account_id": account_id,
            "address": f"{account['username']}@{account['smtp_host']}",
            "total_messages": inbox.total_messages,
            "unread_count": inbox.unread_count,
            "created_at": account["created_at"]
        }
    except Exception as e:
        return {
            "account_id": account_id,
            "address": f"{account['username']}@{account['smtp_host']}",
            "status": "error",
            "error": str(e)
        }

@app.delete("/accounts/{account_id}")
async def delete_account(
    account_id: str,
    auth: bool = Depends(verify_api_key)
):
    """Delete an account"""
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    del accounts[account_id]
    return {"status": "deleted", "account_id": account_id}

# === MESSAGES ===

@app.get("/accounts/{account_id}/messages")
async def get_messages(
    account_id: str,
    folder: str = "INBOX",
    limit: int = 10,
    unread_only: bool = False,
    auth: bool = Depends(verify_api_key)
):
    """Get messages from account"""
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = accounts[account_id]
    
    try:
        client = create_enhanced_email_client(
            hostname=account["imap_host"],
            username=account["username"],
            password=account["password"],
            user_id=account.get("user_id"),
            storage_path=DATA_DIR
        )
        
        messages = client.get_messages(folder=folder, limit=limit, unread_only=unread_only)
        client.disconnect()
        
        return {
            "account_id": account_id,
            "count": len(messages),
            "messages": [
                {
                    "id": m.id,
                    "from": m.from_addr,
                    "to": m.to_addr,
                    "subject": m.subject,
                    "date": m.date.isoformat(),
                    "preview": m.body[:200]
                }
                for m in messages
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/accounts/{account_id}/messages/{msg_id}")
async def get_message(
    account_id: str,
    msg_id: str,
    auth: bool = Depends(verify_api_key)
):
    """Get a specific message"""
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = accounts[account_id]
    
    try:
        client = create_enhanced_email_client(
            hostname=account["imap_host"],
            username=account["username"],
            password=account["password"],
            user_id=account.get("user_id"),
            storage_path=DATA_DIR
        )
        
        message = client.get_message(msg_id)
        client.disconnect()
        
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        return {
            "id": message.id,
            "from": message.from_addr,
            "to": message.to_addr,
            "subject": message.subject,
            "body": message.body,
            "date": message.date.isoformat(),
            "attachments": message.attachments
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === SEND ===

@app.post("/accounts/{account_id}/send")
async def send_email(
    account_id: str,
    request: SendEmailRequest,
    auth: bool = Depends(verify_api_key)
):
    """Send an email"""
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = accounts[account_id]
    
    try:
        client = create_enhanced_email_client(
            hostname=account["smtp_host"],
            username=account["username"],
            password=account["password"],
            user_id=account.get("user_id"),
            storage_path=DATA_DIR
        )
        
        result = client.send(
            to_addr=request.to_addr,
            subject=request.subject,
            body=request.body,
            from_addr=request.from_addr,
            html=request.html
        )
        client.disconnect()
        
        if result:
            return {"status": "sent"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === ACTIONS ===

@app.post("/accounts/{account_id}/messages/{msg_id}/read")
async def mark_read(
    account_id: str,
    msg_id: str,
    auth: bool = Depends(verify_api_key)
):
    """Mark message as read"""
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = accounts[account_id]
    
    try:
        client = create_enhanced_email_client(
            hostname=account["imap_host"],
            username=account["username"],
            password=account["password"],
            user_id=account.get("user_id"),
            storage_path=DATA_DIR
        )
        
        client.mark_as_read(msg_id)
        client.disconnect()
        
        return {"status": "marked_read", "message_id": msg_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/accounts/{account_id}/messages/{msg_id}")
async def delete_message(
    account_id: str,
    msg_id: str,
    auth: bool = Depends(verify_api_key)
):
    """Delete a message"""
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = accounts[account_id]
    
    try:
        client = create_enhanced_email_client(
            hostname=account["imap_host"],
            username=account["username"],
            password=account["password"],
            user_id=account.get("user_id"),
            storage_path=DATA_DIR
        )
        
        client.delete_message(msg_id)
        client.disconnect()
        
        return {"status": "deleted", "message_id": msg_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === MEMORY ===

@app.post("/accounts/{account_id}/memory/save")
async def save_to_memory(
    account_id: str,
    msg_id: str = None,
    auth: bool = Depends(verify_api_key)
):
    """Save email to memory"""
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = accounts[account_id]
    
    try:
        client = create_enhanced_email_client(
            hostname=account["imap_host"],
            username=account["username"],
            password=account["password"],
            user_id=account.get("user_id"),
            storage_path=DATA_DIR
        )
        
        result = client.save_to_memory(msg_id=msg_id)
        client.disconnect()
        
        return {"status": "ok", "saved": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/accounts/{account_id}/memory/search")
async def search_memory(
    account_id: str,
    query: str,
    limit: int = 10,
    auth: bool = Depends(verify_api_key)
):
    """Search saved emails"""
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = accounts[account_id]
    
    try:
        client = create_enhanced_email_client(
            hostname=account["imap_host"],
            username=account["username"],
            password=account["password"],
            user_id=account.get("user_id"),
            storage_path=DATA_DIR
        )
        
        results = client.search_memory(query, limit)
        client.disconnect()
        
        return {"results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/accounts/{account_id}/memory/emails")
async def get_saved_emails(
    account_id: str,
    limit: int = 20,
    auth: bool = Depends(verify_api_key)
):
    """Get all saved emails"""
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = accounts[account_id]
    
    try:
        client = create_enhanced_email_client(
            hostname=account["imap_host"],
            username=account["username"],
            password=account["password"],
            user_id=account.get("user_id"),
            storage_path=DATA_DIR
        )
        
        emails = client.get_saved_emails(limit)
        client.disconnect()
        
        return {"emails": emails, "count": len(emails)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === LLM AUTO-REPLY ===

@app.post("/accounts/{account_id}/reply/generate")
async def generate_reply(
    account_id: str,
    request: GenerateReplyRequest,
    auth: bool = Depends(verify_api_key)
):
    """Generate AI reply"""
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = accounts[account_id]
    
    try:
        client = create_enhanced_email_client(
            hostname=account["imap_host"],
            username=account["username"],
            password=account["password"],
            user_id=account.get("user_id"),
            storage_path=DATA_DIR
        )
        
        result = client.generate_reply(
            original_subject=request.subject,
            original_body=request.body,
            from_addr=request.from_addr,
            context=request.context,
            tone=request.tone
        )
        client.disconnect()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/accounts/{account_id}/reply/auto")
async def send_auto_reply(
    account_id: str,
    msg_id: str,
    request: AutoReplyRequest,
    auth: bool = Depends(verify_api_key)
):
    """Send auto-reply to message"""
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = accounts[account_id]
    
    try:
        client = create_enhanced_email_client(
            hostname=account["imap_host"],
            username=account["username"],
            password=account["password"],
            user_id=account.get("user_id"),
            storage_path=DATA_DIR
        )
        
        result = client.send_auto_reply(
            original_msg_id=msg_id,
            tone=request.tone,
            context=request.context
        )
        client.disconnect()
        
        return {"status": "sent" if result else "failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/accounts/{account_id}/summarize/{msg_id}")
async def summarize_email(
    account_id: str,
    msg_id: str,
    auth: bool = Depends(verify_api_key)
):
    """Summarize an email"""
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = accounts[account_id]
    
    try:
        client = create_enhanced_email_client(
            hostname=account["imap_host"],
            username=account["username"],
            password=account["password"],
            user_id=account.get("user_id"),
            storage_path=DATA_DIR
        )
        
        summary = client.summarize_email(msg_id=msg_id)
        actions = client.suggest_actions(msg_id=msg_id)
        client.disconnect()
        
        return {"summary": summary, "suggested_actions": actions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === WEBHOOKS ===

@app.get("/accounts/{account_id}/webhooks")
async def list_webhooks(
    account_id: str,
    auth: bool = Depends(verify_api_key)
):
    """List webhooks"""
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = accounts[account_id]
    
    try:
        client = create_enhanced_email_client(
            hostname=account["imap_host"],
            username=account["username"],
            password=account["password"],
            user_id=account.get("user_id"),
            storage_path=DATA_DIR
        )
        
        webhooks = client.list_webhooks()
        client.disconnect()
        
        return {"webhooks": [w.to_dict() for w in webhooks]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/accounts/{account_id}/webhooks")
async def create_webhook(
    account_id: str,
    request: WebhookRequest,
    auth: bool = Depends(verify_api_key)
):
    """Create webhook"""
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = accounts[account_id]
    
    try:
        client = create_enhanced_email_client(
            hostname=account["imap_host"],
            username=account["username"],
            password=account["password"],
            user_id=account.get("user_id"),
            storage_path=DATA_DIR
        )
        
        webhook = client.create_webhook(
            name=request.name,
            url=request.url,
            trigger_type=EmailTrigger(request.trigger_type),
            trigger_value=request.trigger_value,
            auto_reply=request.auto_reply,
            reply_template=request.reply_template
        )
        client.disconnect()
        
        return webhook.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/accounts/{account_id}/webhooks/{webhook_id}")
async def delete_webhook(
    account_id: str,
    webhook_id: str,
    auth: bool = Depends(verify_api_key)
):
    """Delete webhook"""
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = accounts[account_id]
    
    try:
        client = create_enhanced_email_client(
            hostname=account["imap_host"],
            username=account["username"],
            password=account["password"],
            user_id=account.get("user_id"),
            storage_path=DATA_DIR
        )
        
        result = client.delete_webhook(webhook_id)
        client.disconnect()
        
        return {"status": "deleted" if result else "not_found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/accounts/{account_id}/webhooks/logs")
async def get_webhook_logs(
    account_id: str,
    webhook_id: str = None,
    limit: int = 50,
    auth: bool = Depends(verify_api_key)
):
    """Get webhook logs"""
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = accounts[account_id]
    
    try:
        client = create_enhanced_email_client(
            hostname=account["imap_host"],
            username=account["username"],
            password=account["password"],
            user_id=account.get("user_id"),
            storage_path=DATA_DIR
        )
        
        logs = client.get_webhook_logs(webhook_id, limit)
        client.disconnect()
        
        return {"logs": [
            {
                "webhook_id": l.webhook_id,
                "event": l.event.value,
                "success": l.success,
                "timestamp": l.timestamp
            }
            for l in logs
        ]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === HEALTH ===

@app.get("/health")

@app.post("/webhooks/email/receive")
async def receive_email_webhook(payload: dict = None):
    import logging
    logging.info(f"Received webhook: {payload}")
    return {"status": "received"}

@app.get("/webhooks/email/receive")
async def webhook_health():
    return {"status": "healthy"}
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "accounts": len(accounts),
        "features": {
            "memory": True,
            "webhooks": True,
            "llm_reply": True
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)


# Webhook endpoint for receiving emails
@app.post("/webhooks/email/receive")
async def receive_email_webhook(payload: dict = None):
    """
    Webhook endpoint for receiving incoming emails from Resend
    """
    import logging
    logging.info(f"Received webhook: {payload}")
    return {"status": "received"}


@app.get("/webhooks/email/receive")
async def webhook_health():
    """Health check for webhook"""
    return {"status": "healthy"}
