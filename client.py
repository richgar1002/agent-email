"""
Decentralized Email Client for AI Agents
Core client library
"""
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime
import poplib

@dataclass
class EmailMessage:
    """Represents an email message"""
    id: str
    from_addr: str
    to_addr: str
    subject: str
    body: str
    date: datetime
    attachments: List[str] = None
    read: bool = False
    
    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []

@dataclass
class Inbox:
    """Represents an inbox"""
    username: str
    address: str
    total_messages: int = 0
    unread_count: int = 0

class EmailClient:
    """Email client for AI agents"""
    
    def __init__(
        self,
        hostname: str,
        username: str,
        password: str,
        smtp_port: int = 587,
        imap_port: int = 993,
        use_ssl: bool = True
    ):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.smtp_port = smtp_port
        self.imap_port = imap_port
        self.use_ssl = use_ssl
        
        self.imap = None
        self.smtp = None
    
    def connect_imap(self):
        """Connect to IMAP server"""
        if self.use_ssl:
            self.imap = imaplib.IMAP4_SSL(self.hostname, self.imap_port)
        else:
            self.imap = imaplib.IMAP4(self.hostname, self.imap_port)
        
        self.imap.login(self.username, self.password)
        return self
    
    def connect_smtp(self):
        """Connect to SMTP server"""
        self.smtp = smtplib.SMTP(self.hostname, self.smtp_port)
        if self.use_ssl:
            self.smtp.starttls()
        
        self.smtp.login(self.username, self.password)
        return self
    
    def disconnect(self):
        """Disconnect from both servers"""
        if self.imap:
            try:
                self.imap.logout()
            except:
                pass
        if self.smtp:
            try:
                self.smtp.quit()
            except:
                pass
    
    # --- Receiving emails ---
    
    def get_inbox(self, folder: str = "INBOX") -> Inbox:
        """Get inbox status"""
        self.connect_imap()
        try:
            self.imap.select(folder)
            status, counts = self.imap.status(folder, "(MESSAGES UNSEEN)")
            total = int(counts[0].decode().split()[2].strip(')('))
            unread = int(status[0].decode().split()[1].strip(')('))
            
            return Inbox(
                username=self.username,
                address=f"{self.username}@{self.hostname}",
                total_messages=total,
                unread_count=unread
            )
        finally:
            self.disconnect()
    
    def get_messages(
        self,
        folder: str = "INBOX",
        limit: int = 10,
        unread_only: bool = False
    ) -> List[EmailMessage]:
        """Get recent messages"""
        self.connect_imap()
        try:
            self.imap.select(folder)
            
            # Search criteria
            if unread_only:
                search_criteria = "UNSEEN"
            else:
                search_criteria = "ALL"
            
            status, message_ids = self.imap.search(None, search_criteria)
            ids = message_ids[0].split()[-limit:]
            
            messages = []
            for msg_id in ids:
                msg = self._fetch_message(msg_id.decode())
                if msg:
                    messages.append(msg)
            
            return messages
        finally:
            self.disconnect()
    
    def get_message(self, msg_id: str) -> Optional[EmailMessage]:
        """Get a specific message"""
        self.connect_imap()
        try:
            return self._fetch_message(msg_id)
        finally:
            self.disconnect()
    
    def _fetch_message(self, msg_id: str) -> Optional[EmailMessage]:
        """Fetch and parse a message"""
        try:
            status, data = self.imap.fetch(msg_id, "(RFC822)")
            raw_email = data[0][1]
            
            msg = email.message_from_bytes(raw_email)
            
            # Extract fields
            subject = msg["subject"] or ""
            from_addr = msg["from"] or ""
            to_addr = msg["to"] or ""
            date = msg["date"] or ""
            
            # Parse body
            body = ""
            attachments = []
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        body = part.get_payload(decode=True).decode()
                    elif content_type == "text/html":
                        if not body:
                            body = part.get_payload(decode=True).decode()
                    elif part.get_filename():
                        attachments.append(part.get_filename())
            else:
                body = msg.get_payload(decode=True).decode()
            
            return EmailMessage(
                id=msg_id,
                from_addr=from_addr,
                to_addr=to_addr,
                subject=subject,
                body=body,
                date=datetime.now(),  # Parse actual date
                attachments=attachments
            )
        except Exception as e:
            print(f"Error fetching message: {e}")
            return None
    
    def mark_as_read(self, msg_id: str):
        """Mark message as read"""
        self.connect_imap()
        try:
            self.imap.store(msg_id, "+FLAGS", "\\Seen")
        finally:
            self.disconnect()
    
    def delete_message(self, msg_id: str):
        """Delete a message"""
        self.connect_imap()
        try:
            self.imap.store(msg_id, "+FLAGS", "\\Deleted")
            self.imap.expunge()
        finally:
            self.disconnect()
    
    # --- Sending emails ---
    
    def send(
        self,
        to_addr: str,
        subject: str,
        body: str,
        from_addr: str = None,
        html: bool = False,
        attachments: List[str] = None
    ) -> bool:
        """Send an email"""
        self.connect_smtp()
        try:
            from_addr = from_addr or self.username
            
            msg = MIMEMultipart()
            msg["From"] = from_addr
            msg["To"] = to_addr
            msg["Subject"] = subject
            
            # Body
            content_type = "html" if html else "plain"
            msg.attach(MIMEText(body, content_type))
            
            # Attachments
            if attachments:
                for filepath in attachments:
                    with open(filepath, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename={filepath}")
                    msg.attach(part)
            
            self.smtp.send_message(msg)
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
        finally:
            self.disconnect()
    
    def send_raw(self, to_addr: str, raw_email: str) -> bool:
        """Send raw email"""
        self.connect_smtp()
        try:
            self.smtp.sendmail(self.username, to_addr, raw_email)
            return True
        except Exception as e:
            print(f"Error sending raw email: {e}")
            return False
        finally:
            self.disconnect()
    
    # --- Management ---
    
    def create_folder(self, name: str):
        """Create a new folder"""
        self.connect_imap()
        try:
            self.imap.create(name)
        finally:
            self.disconnect()
    
    def delete_folder(self, name: str):
        """Delete a folder"""
        self.connect_imap()
        try:
            self.imap.delete(name)
        finally:
            self.disconnect()
    
    def move_message(self, msg_id: str, folder: str):
        """Move message to folder"""
        self.connect_imap()
        try:
            self.imap.move(msg_id, folder)
        finally:
            self.disconnect()
    
    def search(self, query: str, folder: str = "INBOX") -> List[EmailMessage]:
        """Search emails"""
        self.connect_imap()
        try:
            self.imap.select(folder)
            status, message_ids = self.imap.search(None, query)
            ids = message_ids[0].split()
            
            messages = []
            for msg_id in ids:
                msg = self._fetch_message(msg_id.decode())
                if msg:
                    messages.append(msg)
            
            return messages
        finally:
            self.disconnect()


class POP3Client(EmailClient):
    """POP3 email client (alternative to IMAP)"""
    
    def get_messages(self, limit: int = 10) -> List[EmailMessage]:
        """Get messages via POP3"""
        self.connect_pop3()
        try:
            messages = []
            for i in range(1, min(limit, self.pop.stat()[0]) + 1):
                msg = self._fetch_pop_message(i)
                if msg:
                    messages.append(msg)
            return messages
        finally:
            self.disconnect_pop3()
    
    def connect_pop3(self):
        """Connect to POP3 server"""
        if self.use_ssl:
            self.pop = poplib.POP3_SSL(self.hostname, 995)
        else:
            self.pop = poplib.POP3(self.hostname, 110)
        
        self.pop.user(self.username)
        self.pop.pass_(self.password)
    
    def disconnect_pop3(self):
        """Disconnect from POP3"""
        if self.pop:
            try:
                self.pop.quit()
            except:
                pass
    
    def _fetch_pop_message(self, msg_num: int) -> Optional[EmailMessage]:
        """Fetch POP3 message"""
        try:
            lines = self.pop.retr(msg_num)[1]
            raw_email = b"\r\n".join(lines).decode()
            msg = email.message_from_string(raw_email)
            
            return EmailMessage(
                id=str(msg_num),
                from_addr=msg["from"] or "",
                to_addr=msg["to"] or "",
                subject=msg["subject"] or "",
                body=msg.get_payload() or "",
                date=datetime.now()
            )
        except:
            return None


# Factory function
def create_email_client(
    hostname: str,
    username: str,
    password: str,
    protocol: str = "imap"  # or "pop3"
) -> EmailClient:
    """Factory function to create email client"""
    if protocol.lower() == "pop3":
        return POP3Client(hostname, username, password)
    return EmailClient(hostname, username, password)
