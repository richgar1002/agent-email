"""
Email Webhook System
Trigger actions on incoming emails, send replies
"""
import logging
import time
import hashlib
import json
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailTrigger(Enum):
    """Types of email triggers"""
    NEW_EMAIL = "new_email"
    FROM_ADDRESS = "from_address"
    SUBJECT_MATCHES = "subject_matches"
    BODY_CONTAINS = "body_contains"
    ATTACHMENT = "attachment"


class EmailEvent(Enum):
    """Webhook event types"""
    TRIGGERED = "triggered"
    REPLY_SENT = "reply_sent"
    ERROR = "error"
    TEST = "test"


@dataclass
class EmailWebhook:
    """A webhook definition for email"""
    id: str
    name: str
    url: str  # Webhook destination URL
    trigger_type: EmailTrigger
    trigger_value: str  # What to match
    headers: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    auto_reply: bool = False
    reply_template: str = None
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'trigger_type': self.trigger_type.value,
            'trigger_value': self.trigger_value,
            'headers': self.headers,
            'enabled': self.enabled,
            'auto_reply': self.auto_reply,
            'reply_template': self.reply_template,
            'created_at': self.created_at
        }


@dataclass
class EmailWebhookLog:
    """Log of webhook execution"""
    webhook_id: str
    event: EmailEvent
    timestamp: str
    email_data: Dict = field(default_factory=dict)
    response: str = None
    success: bool = True
    error: str = None


class EmailWebhookManager:
    """
    Manage webhooks for email events
    """
    
    WEBHOOKS_FILE = "email_webhooks.json"
    
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path
        self.webhooks: Dict[str, EmailWebhook] = {}
        self.logs: List[EmailWebhookLog] = []
        self._load_webhooks()
    
    def _load_webhooks(self):
        """Load webhooks from storage"""
        if not self.storage_path:
            return
        
        try:
            file_path = f"{self.storage_path}/{self.WEBHOOKS_FILE}"
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            for wh_data in data.get('webhooks', []):
                trigger_type = EmailTrigger(wh_data['trigger_type'])
                self.webhooks[wh_data['id']] = EmailWebhook(
                    id=wh_data['id'],
                    name=wh_data['name'],
                    url=wh_data['url'],
                    trigger_type=trigger_type,
                    trigger_value=wh_data['trigger_value'],
                    headers=wh_data.get('headers', {}),
                    enabled=wh_data.get('enabled', True),
                    auto_reply=wh_data.get('auto_reply', False),
                    reply_template=wh_data.get('reply_template'),
                    created_at=wh_data.get('created_at')
                )
                
        except FileNotFoundError:
            logger.info("No webhooks file found")
        except Exception as e:
            logger.error(f"Error loading webhooks: {e}")
    
    def _save_webhooks(self):
        """Save webhooks to storage"""
        if not self.storage_path:
            return
        
        try:
            file_path = f"{self.storage_path}/{self.WEBHOOKS_FILE}"
            data = {
                'webhooks': [wh.to_dict() for wh in self.webhooks.values()]
            }
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving webhooks: {e}")
    
    # --- CRUD ---
    
    def create_webhook(
        self,
        name: str,
        url: str,
        trigger_type: EmailTrigger,
        trigger_value: str,
        headers: Dict[str, str] = None,
        auto_reply: bool = False,
        reply_template: str = None
    ) -> EmailWebhook:
        """Create a new webhook"""
        webhook_id = f"wh_{hashlib.md5(f'{name}{time.time()}'.encode()).hexdigest()[:8]}"
        
        webhook = EmailWebhook(
            id=webhook_id,
            name=name,
            url=url,
            trigger_type=trigger_type,
            trigger_value=trigger_value,
            headers=headers or {},
            auto_reply=auto_reply,
            reply_template=reply_template
        )
        
        self.webhooks[webhook_id] = webhook
        self._save_webhooks()
        
        logger.info(f"Created email webhook: {name}")
        return webhook
    
    def get_webhook(self, webhook_id: str) -> Optional[EmailWebhook]:
        """Get a webhook by ID"""
        return self.webhooks.get(webhook_id)
    
    def list_webhooks(self, enabled_only: bool = False) -> List[EmailWebhook]:
        """List all webhooks"""
        webhooks = list(self.webhooks.values())
        if enabled_only:
            webhooks = [w for w in webhooks if w.enabled]
        return webhooks
    
    def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook"""
        if webhook_id in self.webhooks:
            del self.webhooks[webhook_id]
            self._save_webhooks()
            return True
        return False
    
    def toggle_webhook(self, webhook_id: str) -> bool:
        """Toggle webhook enabled/disabled"""
        webhook = self.get_webhook(webhook_id)
        if webhook:
            webhook.enabled = not webhook.enabled
            self._save_webhooks()
            return True
        return False
    
    # --- Triggering ---
    
    def check_triggers(self, email_data: Dict, email_client=None) -> List[EmailWebhook]:
        """Check if any webhooks should trigger"""
        triggered = []
        
        from_addr = email_data.get('from_addr', '')
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        
        for webhook in self.webhooks.values():
            if not webhook.enabled:
                continue
            
            # Check trigger condition
            should_trigger = False
            
            if webhook.trigger_type == EmailTrigger.NEW_EMAIL:
                should_trigger = True
            elif webhook.trigger_type == EmailTrigger.FROM_ADDRESS:
                should_trigger = webhook.trigger_value.lower() in from_addr.lower()
            elif webhook.trigger_type == EmailTrigger.SUBJECT_MATCHES:
                should_trigger = webhook.trigger_value.lower() in subject.lower()
            elif webhook.trigger_type == EmailTrigger.BODY_CONTAINS:
                should_trigger = webhook.trigger_value.lower() in body.lower()
            elif webhook.trigger_type == EmailTrigger.ATTACHMENT:
                should_trigger = 'attachments' in email_data
            
            if should_trigger:
                triggered.append(webhook)
                
                # Fire asynchronously
                threading.Thread(
                    target=self._fire_webhook,
                    args=(webhook, email_data, email_client)
                ).start()
        
        return triggered
    
    def _fire_webhook(self, webhook: EmailWebhook, email_data: Dict, email_client=None):
        """Fire a webhook"""
        import requests
        
        payload = {
            'event': webhook.trigger_type.value,
            'trigger_value': webhook.trigger_value,
            'email': email_data,
            'timestamp': datetime.now().isoformat()
        }
        
        log = EmailWebhookLog(
            webhook_id=webhook.id,
            event=EmailEvent.TRIGGERED,
            timestamp=datetime.now().isoformat(),
            email_data=email_data
        )
        
        # Handle auto-reply
        if webhook.auto_reply and email_client and webhook.reply_template:
            try:
                # Generate reply
                reply_body = self._generate_reply(email_data, webhook.reply_template)
                
                # Send reply
                email_client.send(
                    to_addr=email_data.get('from_addr', ''),
                    subject=f"Re: {email_data.get('subject', '')}",
                    body=reply_body
                )
                
                log.event = EmailEvent.REPLY_SENT
                logger.info(f"Auto-reply sent for: {email_data.get('subject', '')}")
                
            except Exception as e:
                log.error = f"Auto-reply failed: {e}"
                logger.error(f"Auto-reply failed: {e}")
        
        # Fire webhook URL
        if webhook.url:
            try:
                response = requests.post(
                    webhook.url,
                    json=payload,
                    headers={
                        'Content-Type': 'application/json',
                        **webhook.headers
                    },
                    timeout=10
                )
                
                log.response = response.text
                log.success = response.status_code < 400
                
                logger.info(f"Webhook fired: {webhook.name} - {response.status_code}")
                
            except Exception as e:
                log.success = False
                log.error = str(e)
                logger.error(f"Webhook failed: {webhook.name} - {e}")
        
        self.logs.append(log)
    
    def _generate_reply(self, email_data: Dict, template: str) -> str:
        """Generate auto-reply from template"""
        subject = email_data.get('subject', '')
        from_addr = email_data.get('from_addr', '')
        
        reply = template.replace('{{subject}}', subject)
        reply = reply.replace('{{from}}', from_addr)
        reply = reply.replace('{{body}}', email_data.get('body', '')[:500])
        
        return reply
    
    def test_webhook(self, webhook_id: str) -> bool:
        """Test a webhook"""
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return False
        
        test_data = {
            'from_addr': 'test@example.com',
            'subject': 'Test Email',
            'body': 'This is a test'
        }
        
        self._fire_webhook(webhook, test_data, None)
        return True
    
    def get_logs(self, webhook_id: str = None, limit: int = 50) -> List[EmailWebhookLog]:
        """Get webhook execution logs"""
        logs = self.logs
        if webhook_id:
            logs = [l for l in logs if l.webhook_id == webhook_id]
        return logs[-limit:]


def create_email_webhook_manager(storage_path: str = None) -> EmailWebhookManager:
    """Factory function"""
    return EmailWebhookManager(storage_path)
