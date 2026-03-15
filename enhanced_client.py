"""
Enhanced Email Client
Complete email client with memory, webhooks, and LLM
"""
import os
import logging
from pathlib import Path
from typing import List, Dict, Optional

# Import base client
from client import EmailClient, create_email_client, EmailMessage

# Import new modules
from memory_integration import EmailMemory, EmailSummary, create_email_memory
from webhook_manager import EmailWebhookManager, EmailTrigger, create_email_webhook_manager
from llm_reply import LLMReply, create_llm_reply

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedEmailClient:
    """
    Enhanced email client with all integrations
    """
    
    def __init__(
        self,
        hostname: str,
        username: str,
        password: str,
        user_id: str = None,
        storage_path: str = None
    ):
        # Base client
        self.hostname = hostname
        self.username = username
        self.password = password
        
        # Create base email client
        self.client = create_email_client(hostname, username, password)
        
        # Storage path
        self.storage_path = storage_path or "/tmp/email_data"
        os.makedirs(self.storage_path, exist_ok=True)
        
        # === INTEGRATED MODULES ===
        
        # Memory
        self.memory: EmailMemory = None
        self._init_memory(user_id)
        
        # Webhooks
        self.webhooks = create_email_webhook_manager(self.storage_path)
        
        # LLM Reply
        self.llm = create_llm_reply()
        
        logger.info(f"Enhanced email client initialized for {username}")
    
    def _init_memory(self, user_id: str = None):
        """Initialize memory integration"""
        try:
            self.memory = create_email_memory(user_id)
            logger.info("Memory integration enabled")
        except Exception as e:
            logger.warning(f"Memory not available: {e}")
    
    # === CORE EMAIL OPERATIONS ===
    
    def get_inbox(self, folder: str = "INBOX"):
        """Get inbox status"""
        return self.client.get_inbox(folder)
    
    def get_messages(self, folder: str = "INBOX", limit: int = 10, unread_only: bool = False) -> List[EmailMessage]:
        """Get messages"""
        return self.client.get_messages(folder, limit, unread_only)
    
    def get_message(self, msg_id: str) -> Optional[EmailMessage]:
        """Get specific message"""
        return self.client.get_message(msg_id)
    
    def send(self, to_addr: str, subject: str, body: str, **kwargs) -> bool:
        """Send email"""
        return self.client.send(to_addr, subject, body, **kwargs)
    
    def mark_as_read(self, msg_id: str):
        """Mark as read"""
        return self.client.mark_as_read(msg_id)
    
    def delete_message(self, msg_id: str):
        """Delete message"""
        return self.client.delete_message(msg_id)
    
    def search(self, query: str, folder: str = "INBOX") -> List[EmailMessage]:
        """Search emails"""
        return self.client.search(query, folder)
    
    def disconnect(self):
        """Disconnect"""
        self.client.disconnect()
    
    # === MEMORY INTEGRATION ===
    
    def save_to_memory(self, msg_id: str = None, email_data: Dict = None) -> bool:
        """Save email to memory"""
        if not self.memory:
            logger.warning("Memory not initialized")
            return False
        
        try:
            # Get email if ID provided
            if msg_id and not email_data:
                msg = self.client.get_message(msg_id)
                if msg:
                    email_data = {
                        'from_addr': msg.from_addr,
                        'to_addr': msg.to_addr,
                        'subject': msg.subject,
                        'body': msg.body,
                        'date': str(msg.date)
                    }
            
            if not email_data:
                return False
            
            summary = EmailSummary(
                from_addr=email_data.get('from_addr', ''),
                to_addr=email_data.get('to_addr', ''),
                subject=email_data.get('subject', ''),
                body=email_data.get('body', ''),
                date=email_data.get('date')
            )
            
            result = self.memory.save_email(summary)
            
            if result:
                # Check webhooks
                self.webhooks.check_triggers(email_data, self.client)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to save to memory: {e}")
            return False
    
    def check_new_emails(self, save_memory: bool = True) -> List[EmailMessage]:
        """Check for new emails, optionally save to memory"""
        messages = self.client.get_messages(unread_only=True)
        
        for msg in messages:
            if save_memory:
                self.save_to_memory(email_data={
                    'from_addr': msg.from_addr,
                    'to_addr': msg.to_addr,
                    'subject': msg.subject,
                    'body': msg.body,
                    'date': str(msg.date)
                })
        
        return messages
    
    def search_memory(self, query: str, limit: int = 10) -> List[Dict]:
        """Search saved emails"""
        if not self.memory:
            return []
        return self.memory.search_emails(query, limit)
    
    def get_saved_emails(self, limit: int = 20) -> List[Dict]:
        """Get all saved emails"""
        if not self.memory:
            return []
        return self.memory.get_saved_emails(limit)
    
    # === LLM AUTO-REPLY ===
    
    def generate_reply(
        self,
        original_subject: str,
        original_body: str,
        from_addr: str,
        context: str = None,
        tone: str = "professional"
    ) -> Dict:
        """Generate AI reply"""
        result = self.llm.generate_reply(
            email_subject=original_subject,
            email_body=original_body,
            from_addr=from_addr,
            context=context,
            tone=tone
        )
        
        return {
            'reply': result.reply_text,
            'confidence': result.confidence,
            'error': result.error
        }
    
    def send_auto_reply(
        self,
        original_msg_id: str,
        tone: str = "professional",
        context: str = None
    ) -> bool:
        """Generate and send auto-reply"""
        msg = self.client.get_message(original_msg_id)
        if not msg:
            return False
        
        # Generate reply
        result = self.llm.generate_reply(
            email_subject=msg.subject,
            email_body=msg.body,
            from_addr=msg.from_addr,
            context=context,
            tone=tone
        )
        
        if not result.reply_text:
            logger.error("Failed to generate reply")
            return False
        
        # Send reply
        success = self.send(
            to_addr=msg.from_addr,
            subject=f"Re: {msg.subject}",
            body=result.reply_text
        )
        
        if success:
            self.client.mark_as_read(original_msg_id)
        
        return success
    
    def summarize_email(self, msg_id: str = None, email_data: Dict = None) -> str:
        """Summarize an email"""
        if msg_id and not email_data:
            msg = self.client.get_message(msg_id)
            if msg:
                email_data = {
                    'subject': msg.subject,
                    'body': msg.body
                }
        
        if not email_data:
            return ""
        
        return self.llm.generate_summary(
            email_subject=email_data.get('subject', ''),
            email_body=email_data.get('body', '')
        )
    
    def suggest_actions(self, msg_id: str = None, email_data: Dict = None) -> List[str]:
        """Suggest actions from email"""
        if msg_id and not email_data:
            msg = self.client.get_message(msg_id)
            if msg:
                email_data = {'body': msg.body}
        
        if not email_data:
            return []
        
        return self.llm.suggest_actions(email_data.get('body', ''))
    
    # === WEBHOOKS ===
    
    def create_webhook(
        self,
        name: str,
        url: str,
        trigger_type: EmailTrigger,
        trigger_value: str,
        auto_reply: bool = False,
        reply_template: str = None
    ):
        """Create webhook"""
        return self.webhooks.create_webhook(
            name=name,
            url=url,
            trigger_type=trigger_type,
            trigger_value=trigger_value,
            auto_reply=auto_reply,
            reply_template=reply_template
        )
    
    def list_webhooks(self):
        """List webhooks"""
        return self.webhooks.list_webhooks()
    
    def delete_webhook(self, webhook_id: str) -> bool:
        """Delete webhook"""
        return self.webhooks.delete_webhook(webhook_id)
    
    def test_webhook(self, webhook_id: str) -> bool:
        """Test webhook"""
        return self.webhooks.test_webhook(webhook_id)
    
    def get_webhook_logs(self, webhook_id: str = None, limit: int = 50):
        """Get webhook logs"""
        return self.webhooks.get_logs(webhook_id, limit)


def create_enhanced_email_client(
    hostname: str,
    username: str,
    password: str,
    user_id: str = None,
    storage_path: str = None
) -> EnhancedEmailClient:
    """Factory function"""
    return EnhancedEmailClient(hostname, username, password, user_id, storage_path)
