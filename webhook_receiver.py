"""
Simple Webhook Receiver for Resend Incoming Emails
"""
from fastapi import FastAPI, Request
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.post("/webhooks/email/receive")
async def receive_email(request: Request):
    """Receive incoming email from Resend"""
    body = await request.json()
    logger.info(f"Received email: {body}")
    
    # Process the email
    # TODO: Store in database, forward to user, etc.
    
    return {"status": "received"}

@app.get("/webhooks/email/receive")
async def webhook_health():
    """Health check"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
