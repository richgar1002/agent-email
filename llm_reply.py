"""
LLM Auto-Reply for Email
AI-powered responses to incoming emails
"""
import logging
from typing import Dict, Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ReplyResult:
    """Result of LLM reply generation"""
    reply_text: str
    confidence: float = 1.0
    suggested_subject: str = None
    error: str = None


class LLMReply:
    """
    Generate AI-powered replies to emails
    """
    
    def __init__(self):
        self.ollama_available = False
        self.model = "llama3.2"
        self._check_ollama()
    
    def _check_ollama(self):
        """Check if Ollama is available"""
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            self.ollama_available = response.status_code == 200
            if self.ollama_available:
                logger.info("Ollama available for auto-replies")
        except (requests.RequestException, ConnectionError, TimeoutError):
            logger.info("Ollama not available, using templates")
    
    def generate_reply(
        self,
        email_subject: str,
        email_body: str,
        from_addr: str,
        context: str = None,
        tone: str = "professional"
    ) -> ReplyResult:
        """
        Generate an AI reply to an email
        
        Args:
            email_subject: Original email subject
            email_body: Original email body
            from_addr: Sender email address
            context: Additional context for the AI
            tone: Tone of the reply (professional, casual, brief)
        
        Returns:
            ReplyResult with generated reply
        """
        if not self.ollama_available:
            # Fall back to template
            return self._template_reply(email_subject, from_addr, tone)
        
        try:
            prompt = self._build_prompt(
                email_subject, email_body, from_addr, context, tone
            )
            
            import requests
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                reply_text = result.get('response', '').strip()
                
                return ReplyResult(
                    reply_text=reply_text,
                    confidence=0.9
                )
            else:
                return ReplyResult(
                    reply_text="",
                    error=f"Ollama error: {response.status_code}"
                )
                
        except Exception as e:
            logger.error(f"LLM reply failed: {e}")
            return ReplyResult(
                reply_text="",
                error=str(e)
            )
    
    def _build_prompt(
        self,
        subject: str,
        body: str,
        from_addr: str,
        context: str,
        tone: str
    ) -> str:
        """Build prompt for LLM"""
        
        base_prompt = f"""You are an AI email assistant. Generate a reply to this email.

ORIGINAL EMAIL:
From: {from_addr}
Subject: {subject}
Body:
{body}

"""
        
        if context:
            base_prompt += f"CONTEXT:\n{context}\n\n"
        
        base_prompt += f"""INSTRUCTIONS:
- Write in a {tone} tone
- Keep the reply concise and relevant
- If action is needed, mention it clearly
- Do not make up information
- Sign off professionally

REPLY:"""

        return base_prompt
    
    def _template_reply(
        self,
        subject: str,
        from_addr: str,
        tone: str
    ) -> ReplyResult:
        """Generate template-based reply when LLM unavailable"""
        
        templates = {
            "professional": f"Thank you for your email regarding '{subject}'.\n\nI will review this and get back to you shortly.\n\nBest regards",
            "casual": f"Hey,\n\nThanks for reaching out about '{subject}'. I'll take a look and circle back soon!\n\nCheers",
            "brief": f"Received. Will respond shortly."
        }
        
        reply = templates.get(tone, templates["professional"])
        
        return ReplyResult(
            reply_text=reply,
            confidence=0.5,
            error="Used template (Ollama unavailable)"
        )
    
    def generate_summary(self, email_subject: str, email_body: str) -> str:
        """Generate a summary of the email"""
        if not self.ollama_available:
            return email_body[:200] + "..."
        
        try:
            prompt = f"""Summarize this email in 2-3 sentences:

Subject: {email_subject}
Body:
{email_body}

SUMMARY:"""

            import requests
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            
        except Exception as e:
            logger.error(f"Summary failed: {e}")
        
        return email_body[:200]
    
    def suggest_actions(self, email_body: str) -> list:
        """Suggest actions based on email content"""
        if not self.ollama_available:
            return []
        
        try:
            prompt = f"""Analyze this email and suggest any required actions. 
List as bullet points. If no actions needed, say "No action required".

Email:
{email_body[:1000]}

ACTIONS:"""

            import requests
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result.get('response', '').strip()
                
                # Parse bullet points
                actions = [
                    line.strip('- ').strip() 
                    for line in text.split('\n') 
                    if line.strip()
                ]
                return actions
            
        except Exception as e:
            logger.error(f"Action suggestion failed: {e}")
        
        return []


def create_llm_reply() -> LLMReply:
    """Factory function"""
    return LLMReply()
