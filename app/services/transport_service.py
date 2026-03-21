"""Transport Service - handles email sending/receiving via various providers"""
import logging
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class EmailTransport(ABC):
    """Base class for email transport providers"""
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to the email provider"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Disconnect from the provider"""
        pass
    
    @abstractmethod
    def fetch_messages(self, folder: str = "INBOX", limit: int = 10, unread_only: bool = False) -> List[Dict]:
        """Fetch messages from inbox"""
        pass
    
    @abstractmethod
    def get_message(self, message_id: str) -> Optional[Dict]:
        """Get a specific message"""
        pass
    
    @abstractmethod
    def send_message(
        self,
        to_addrs: List[str],
        subject: str,
        body: str,
        from_addr: str = None,
        html: bool = False,
        attachments: List[Dict] = None
    ) -> bool:
        """Send an email"""
        pass
    
    @abstractmethod
    def mark_as_read(self, message_id: str):
        """Mark message as read"""
        pass
    
    @abstractmethod
    def delete_message(self, message_id: str):
        """Delete a message"""
        pass


class SMTPIMAPTransport(EmailTransport):
    """SMTP/IMAP transport using existing client"""
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        imap_host: str,
        imap_port: int,
        username: str,
        password: str
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.imap_host = imap_host
        self.imap_port = imap_port
        self.username = username
        self.password = password
        self._client = None
    
    def _get_client(self):
        """Lazy load the email client"""
        if self._client is None:
            from enhanced_client import create_enhanced_email_client
            self._client = create_enhanced_email_client(
                hostname=self.imap_host,
                username=self.username,
                password=self.password,
                storage_path="/tmp/email_data"
            )
        return self._client
    
    def connect(self) -> bool:
        """Connect - client connects on first use"""
        try:
            client = self._get_client()
            client.get_inbox()  # Test connection
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect the client"""
        if self._client:
            self._client.disconnect()
            self._client = None
    
    def fetch_messages(self, folder: str = "INBOX", limit: int = 10, unread_only: bool = False) -> List[Dict]:
        """Fetch messages"""
        client = self._get_client()
        messages = client.get_messages(folder=folder, limit=limit, unread_only=unread_only)
        
        return [
            {
                "id": m.id,
                "from": m.from_addr,
                "to": m.to_addr,
                "subject": m.subject,
                "date": str(m.date),
                "preview": m.body[:200] if m.body else ""
            }
            for m in messages
        ]
    
    def get_message(self, message_id: str) -> Optional[Dict]:
        """Get a specific message"""
        client = self._get_client()
        msg = client.get_message(message_id)
        
        if not msg:
            return None
        
        return {
            "id": msg.id,
            "from": msg.from_addr,
            "to": msg.to_addr,
            "subject": msg.subject,
            "body": msg.body,
            "date": str(msg.date),
            "attachments": msg.attachments
        }
    
    def send_message(
        self,
        to_addrs: List[str],
        subject: str,
        body: str,
        from_addr: str = None,
        html: bool = False,
        attachments: List[Dict] = None
    ) -> bool:
        """Send an email"""
        client = self._get_client()
        
        to_addr = to_addrs[0] if to_addrs else ""
        
        return client.send(
            to_addr=to_addr,
            subject=subject,
            body=body,
            from_addr=from_addr,
            html=html
        )
    
    def mark_as_read(self, message_id: str):
        """Mark message as read"""
        client = self._get_client()
        client.mark_as_read(message_id)
    
    def delete_message(self, message_id: str):
        """Delete a message"""
        client = self._get_client()
        client.delete_message(message_id)


class TransportFactory:
    """Factory for creating transport instances"""
    
    @staticmethod
    def create_transport(provider_type: str, config: Dict[str, Any]) -> EmailTransport:
        """
        Create a transport based on provider type
        """
        
        if provider_type == "smtp_imap":
            return SMTPIMAPTransport(
                smtp_host=config["smtp_host"],
                smtp_port=config.get("smtp_port", 587),
                imap_host=config["imap_host"],
                imap_port=config.get("imap_port", 993),
                username=config["username"],
                password=config["password"]
            )
        
        # Future providers
        # elif provider_type == "gmail":
        #     return GmailTransport(config)
        # elif provider_type == "graph":
        #     return MicrosoftGraphTransport(config)
        
        raise ValueError(f"Unknown provider type: {provider_type}")


class TransportService:
    """
    Service for managing email transports
    """
    
    def __init__(self):
        self._transports: Dict[str, EmailTransport] = {}
    
    def get_transport(self, mailbox_id: str, config: Dict[str, Any]) -> EmailTransport:
        """
        Get or create a transport for a mailbox
        """
        if mailbox_id not in self._transports:
            self._transports[mailbox_id] = TransportFactory.create_transport(
                config["provider_type"],
                config
            )
        
        return self._transports[mailbox_id]
    
    def close_transport(self, mailbox_id: str):
        """Close and remove a transport"""
        if mailbox_id in self._transports:
            self._transports[mailbox_id].disconnect()
            del self._transports[mailbox_id]
    
    def close_all(self):
        """Close all transports"""
        for transport in self._transports.values():
            transport.disconnect()
        self._transports.clear()
