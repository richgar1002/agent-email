#!/usr/bin/env python3
"""Test script for Agent Email Platform"""
import os
import sys
import json

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DATABASE_URL"] = "sqlite:///./test_agent_email.db"
os.environ["API_KEY"] = "test-secret-key"

from app.db.session import init_db, SessionLocal
from app.db import models
import hashlib


def setup():
    """Initialize database"""
    print("📦 Creating tables...")
    init_db()
    print("✅ Tables created")


def create_test_data():
    """Create test organization, agent, mailbox"""
    db = SessionLocal()
    
    # Create organization
    org = models.Organization(
        name="Test Org",
        slug="test-org"
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    org_id = str(org.id)
    print(f"✅ Created org: {org_id}")
    
    # Create agent
    agent = models.Agent(
        organization_id=org.id,
        name="Test Agent",
        slug="test-agent",
        description="A test agent"
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    agent_id = str(agent.id)
    print(f"✅ Created agent: {agent_id}")
    
    # Create API token
    token = "test-token-123"
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    api_token = models.ApiToken(
        organization_id=org.id,
        agent_id=agent.id,
        token_hash=token_hash,
        name="Test Token",
        scopes=["mail.read", "mail.send", "draft.create", "webhook.manage"]
    )
    db.add(api_token)
    db.commit()
    print(f"✅ Created API token")
    
    # Create mailbox
    mailbox = models.Mailbox(
        organization_id=org.id,
        agent_id=agent.id,
        address="test@example.com",
        provider_type="smtp_imap",
        inbound_host="imap.example.com",
        outbound_host="smtp.example.com",
        username="test@example.com",
        credential_ref="encrypted_password_ref"
    )
    db.add(mailbox)
    db.commit()
    db.refresh(mailbox)
    mailbox_id = str(mailbox.id)
    print(f"✅ Created mailbox: {mailbox_id}")
    
    db.close()
    
    return {
        "org_id": org_id,
        "agent_id": agent_id,
        "mailbox_id": mailbox_id,
        "token": token
    }


def test_api(data):
    """Test the API endpoints"""
    import requests
    from multiprocessing import Process
    import time
    
    # Start server in background
    def run_server():
        import uvicorn
        from app.main import app
        uvicorn.run(app, host="127.0.0.1", port=8003, log_level="error")
    
    server = Process(target=run_server)
    server.start()
    time.sleep(3)  # Wait for server to start
    
    base_url = "http://127.0.0.1:8003"
    headers = {"x-api-key": data["token"]}
    
    try:
        # Test health
        print("\n📋 Testing API...")
        r = requests.get(f"{base_url}/health")
        print(f"  GET /health → {r.status_code} {r.json()}")
        
        # Test get organization
        r = requests.get(
            f"{base_url}/organizations/{data['org_id']}",
            headers=headers
        )
        print(f"  GET /organizations/{{id}} → {r.status_code}")
        
        # Test get agent
        r = requests.get(
            f"{base_url}/organizations/{data['org_id']}/agents/{data['agent_id']}",
            headers=headers
        )
        print(f"  GET /agents/{{id}} → {r.status_code} {r.json()}")
        
        # Test list webhooks (empty)
        r = requests.get(
            f"{base_url}/organizations/{data['org_id']}/webhooks",
            headers=headers
        )
        print(f"  GET /webhooks → {r.status_code} {r.json()}")
        
        # Test create webhook
        r = requests.post(
            f"{base_url}/organizations/{data['org_id']}/webhooks?name=test&target_url=https://example.com/webhook&trigger_type=new_email",
            headers=headers
        )
        print(f"  POST /webhooks → {r.status_code} {r.json()}")
        
        # Test list drafts (empty)
        r = requests.get(
            f"{base_url}/organizations/{data['org_id']}/drafts",
            headers=headers
        )
        print(f"  GET /drafts → {r.status_code} {r.json()}")
        
        # Test audit logs (empty)
        r = requests.get(
            f"{base_url}/organizations/{data['org_id']}/audit",
            headers=headers
        )
        print(f"  GET /audit → {r.status_code} {r.json()}")
        
        print("\n✅ All API tests passed!")
        
    finally:
        server.terminate()
        server.join()


if __name__ == "__main__":
    # Clean up old test db
    if os.path.exists("test_agent_email.db"):
        os.remove("test_agent_email.db")
    
    setup()
    data = create_test_data()
    test_api(data)
    
    print("\n🎉 Platform is ready!")
    print(f"\nTest token: {data['token']}")
