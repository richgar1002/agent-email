"""
Decentralized Email API
REST API for AI agents to manage email
"""
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os

from client import create_email_client, EmailMessage

app = FastAPI(title="Agent Email API")

# Config
SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
IMAP_HOST = os.getenv("IMAP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))

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

class SendEmailRequest(BaseModel):
    from_addr: Optional[str] = None
    to_addr: str
    subject: str
    body: str
    html: bool = False

class WebhookRequest(BaseModel):
    url: str
    events: List[str] = ["new_email"]

# Accounts

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
    
    # Try to connect and get inbox status
    try:
        client = create_email_client(
            hostname=account["imap_host"],
            username=account["username"],
            password=account["password"],
            imap_port=account["imap_port"]
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

# Messages

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
        client = create_email_client(
            hostname=account["imap_host"],
            username=account["username"],
            password=account["password"],
            imap_port=account["imap_port"]
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
        client = create_email_client(
            hostname=account["imap_host"],
            username=account["username"],
            password=account["password"],
            imap_port=account["imap_port"]
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

# Send

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
        client = create_email_client(
            hostname=account["smtp_host"],
            username=account["username"],
            password=account["password"],
            smtp_port=account["smtp_port"]
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

# Actions

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
        client = create_email_client(
            hostname=account["imap_host"],
            username=account["username"],
            password=account["password"],
            imap_port=account["imap_port"]
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
        client = create_email_client(
            hostname=account["imap_host"],
            username=account["username"],
            password=account["password"],
            imap_port=account["imap_port"]
        )
        
        client.delete_message(msg_id)
        client.disconnect()
        
        return {"status": "deleted", "message_id": msg_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "accounts": len(accounts)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
