"""Safety Service - treats inbound email as hostile"""
import re
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SafetyResult:
    """Result of safety scan"""
    status: str  # safe, suspicious, blocked
    risks: List[str]
    sanitized_body: str
    links_found: List[str]
    attachments_found: List[str]


class SafetyService:
    """
    Inbound email safety - treat all email as potentially hostile
    """
    
    # Patterns that might indicate malicious content
    SUSPICIOUS_PATTERNS = [
        r'eval\s*\(',
        r'exec\s*\(',
        r'__import__\s*\(',
        r'<script[^>]*>',
        r'javascript:',
        r'on\w+\s*=',
        r'data:text/html',
        r'file:///',
        r'\\UNC\\',
    ]
    
    # Patterns for tool instructions embedded in email
    TOOL_INSTRUCTION_PATTERNS = [
        r'^EXECUTE:',
        r'^RUN:',
        r'^COMMAND:',
        r'\$\(.*\)',  # Command substitution
        r'`.*`',  # Inline commands
    ]
    
    def __init__(self):
        self.suspicious_regex = [re.compile(p, re.IGNORECASE) for p in self.SUSPICIOUS_PATTERNS]
        self.tool_instruction_regex = [re.compile(p, re.MULTILINE) for p in self.TOOL_INSTRUCTION_PATTERNS]
    
    def scan_inbound_email(
        self,
        body_text: str,
        body_html: str = None,
        from_addr: str = None,
        attachments: List[Dict] = None
    ) -> SafetyResult:
        """
        Scan inbound email for safety issues
        """
        risks = []
        links = []
        attachments_found = []
        
        # Extract links
        if body_html:
            links = self._extract_links(body_html)
        
        # Track attachments
        if attachments:
            for att in attachments:
                attachments_found.append(att.get("filename", "unknown"))
        
        # Check for suspicious patterns in plain text
        if body_text:
            for regex in self.suspicious_regex:
                if regex.search(body_text):
                    risks.append(f"Suspicious pattern detected: {regex.pattern}")
            
            # Check for tool instructions
            for regex in self.tool_instruction_regex:
                if regex.search(body_text):
                    risks.append("Potential tool instructions detected in email body")
        
        # Check for suspicious patterns in HTML
        if body_html:
            for regex in self.suspicious_regex:
                if regex.search(body_html):
                    risks.append(f"Suspicious HTML pattern detected")
        
        # Check for too many links (potential phishing)
        if len(links) > 10:
            risks.append(f"Excessive links ({len(links)}) - potential phishing")
        
        # Check for suspicious URLs
        for link in links:
            if self._is_suspicious_link(link):
                risks.append(f"Suspicious link: {link}")
        
        # Check attachments for dangerous types
        dangerous_types = [".exe", ".scr", ".bat", ".cmd", ".vbs", ".js", ".jar", ".sh", ".ps1"]
        for att in attachments_found:
            ext = att.lower().split(".")[-1] if "." in att else ""
            if ext in dangerous_types:
                risks.append(f"Dangerous attachment type: {ext}")
        
        # Determine status
        if any("script" in r.lower() or "eval" in r.lower() for r in risks):
            status = "blocked"
        elif risks:
            status = "suspicious"
        else:
            status = "safe"
        
        # Sanitize body
        sanitized = self._sanitize_body(body_text, body_html)
        
        return SafetyResult(
            status=status,
            risks=risks,
            sanitized_body=sanitized,
            links_found=links,
            attachments_found=attachments_found
        )
    
    def _extract_links(self, html: str) -> List[str]:
        """Extract URLs from HTML"""
        url_pattern = re.compile(r'href=["\'](https?://[^"\']+)["\']', re.IGNORECASE)
        return url_pattern.findall(html)
    
    def _is_suspicious_link(self, url: str) -> bool:
        """Check if a URL is suspicious"""
        url_lower = url.lower()
        
        # IP addresses in URLs
        if re.match(r'https?://\d+\.\d+\.\d+\.\d+', url):
            return True
        
        # Very long URLs
        if len(url) > 200:
            return True
        
        # Known shorteners (might hide real destination)
        shorteners = ["bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly"]
        if any(s in url_lower for s in shorteners):
            # Not necessarily bad, but worth flagging for review
            return False  # Don't block, just note
        
        # Data URLs
        if url_lower.startswith("data:"):
            return True
        
        return False
    
    def _sanitize_body(self, body_text: str, body_html: str = None) -> str:
        """
        Basic sanitization - strips dangerous content
        """
        if not body_text:
            return ""
        
        sanitized = body_text
        
        # Remove potential command injections
        sanitized = re.sub(r'\$\([^)]+\)', '[REMOVED]', sanitized)
        sanitized = re.sub(r'`[^`]+`', '[REMOVED]', sanitized)
        
        # Remove eval/exec references
        sanitized = re.sub(r'eval\s*\([^)]+\)', '[REMOVED]', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'exec\s*\([^)]+\)', '[REMOVED]', sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def check_sender_trust(self, from_addr: str, contact_trust_level: str = None) -> Dict:
        """
        Assess sender trust level
        """
        if contact_trust_level:
            return {
                "trust_level": contact_trust_level,
                "can_auto_reply": contact_trust_level in ["trusted", "internal"],
                "requires_approval": contact_trust_level == "unknown"
            }
        
        # Default assessment based on email
        domain = from_addr.split("@")[1] if "@" in from_addr else ""
        
        # Known safe domains (could be configurable)
        safe_domains = ["google.com", "microsoft.com", "github.com", "apple.com"]
        
        if any(d in domain.lower() for d in safe_domains):
            return {
                "trust_level": "trusted",
                "can_auto_reply": True,
                "requires_approval": False
            }
        
        return {
            "trust_level": "unknown",
            "can_auto_reply": False,
            "requires_approval": True
        }
