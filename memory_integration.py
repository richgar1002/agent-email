"""
Email Memory Integration
Connects Agent Email to Memory Bridge
"""
import os
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ujfmhpbodscrzkwkynon.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


@dataclass
class EmailSummary:
    """Summary of an email"""
    from_addr: str
    to_addr: str
    subject: str
    body: str
    date: str = None
    thread_id: str = None


class EmailMemory:
    """
    Integration between Email and Memory Bridge
    """
    
    def __init__(self, user_id: str = None):
        self.user_id = user_id or "email"
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Supabase client"""
        try:
            from memory_bridge_supabase.client_production import create_memory_client, ClientConfig
            
            config = ClientConfig(
                max_retries=3,
                retry_delay=2.0,
                verbose=False
            )
            
            self.client = create_memory_client(
                supabase_url=SUPABASE_URL,
                supabase_key=SUPABASE_KEY,
                user_id=self.user_id,
                config=config
            )
            logger.info("Email memory client initialized")
            
        except Exception as e:
            logger.warning(f"Could not initialize memory client: {e}")
            self.client = None
    
    def save_email(self, email: EmailSummary, auto_tag: bool = True) -> bool:
        """Save an email to memory"""
        if not self.client:
            logger.warning("Memory client not available")
            return False
        
        try:
            # Auto-generate tags
            tags = ["email"]
            if auto_tag:
                tags.extend(self._generate_tags(email))
            
            # Create memory
            self.client.create_memory(
                title=f"Email: {email.subject}",
                content=f"From: {email.from_addr}\nTo: {email.to_addr}\n\n{email.body}",
                tags=tags,
                source=f"email:{email.thread_id or email.subject}"
            )
            
            logger.info(f"Saved email to memory: {email.subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save email: {e}")
            return False
    
    def _generate_tags(self, email: EmailSummary) -> List[str]:
        """Generate tags based on email content"""
        tags = []
        
        subject_lower = email.subject.lower()
        body_lower = email.body.lower()
        
        # Subject-based tags
        if "trade" in subject_lower or "trade" in body_lower:
            tags.append("trading")
        if "alert" in subject_lower:
            tags.append("alert")
        if "error" in subject_lower or "failed" in subject_lower:
            tags.append("error")
        if "report" in subject_lower:
            tags.append("report")
        
        # Sender domain
        if "@" in email.from_addr:
            domain = email.from_addr.split("@")[1]
            tags.append(f"from:{domain}")
        
        return tags[:5]
    
    def search_emails(self, query: str, limit: int = 10) -> List[Dict]:
        """Search saved emails"""
        if not self.client:
            return []
        
        try:
            results = self.client.search(query, limit=limit)
            # Filter to email sources
            return [r for r in results if r.get('source', '').startswith('email:')]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_saved_emails(self, limit: int = 20) -> List[Dict]:
        """Get all saved emails"""
        if not self.client:
            return []
        
        try:
            memories = self.client.get_memories(limit=limit)
            return [m for m in memories if m.get('source', '').startswith('email:')]
            
        except Exception as e:
            logger.error(f"Failed to get emails: {e}")
            return []


def create_email_memory(user_id: str = None) -> EmailMemory:
    """Factory function"""
    return EmailMemory(user_id)
