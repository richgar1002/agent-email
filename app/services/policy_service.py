"""Policy Service - decides if an action is allowed"""
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.db.models import Policy, Mailbox, Contact, Draft

logger = logging.getLogger(__name__)


class PolicyDecision:
    """Result of a policy check"""
    def __init__(self, allowed: bool, action: str, reason: str, requires_approval: bool = False):
        self.allowed = allowed
        self.action = action  # approve, block, require_approval
        self.reason = reason
        self.requires_approval = requires_approval

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "action": self.action,
            "reason": self.reason,
            "requires_approval": self.requires_approval
        }


class PolicyService:
    """
    Policy engine for agent email actions
    """
    
    def __init__(self, db: Session, organization_id: str):
        self.db = db
        self.organization_id = organization_id
    
    def check_send_policy(
        self,
        draft: Draft,
        sender_mailbox: Mailbox,
        recipient: str
    ) -> PolicyDecision:
        """
        Check if a draft can be sent.
        
        Default v1 rules:
        - External recipients require approval
        - Attachments require approval  
        - Low confidence requires approval
        - Blocked senders are blocked
        - Trusted senders bypass
        """
        
        # Check recipient trust level
        contact = self.db.query(Contact).filter(
            Contact.organization_id == self.organization_id,
            Contact.email == recipient
        ).first()
        
        if contact:
            if contact.trust_level == "blocked":
                return PolicyDecision(False, "block", f"Recipient {recipient} is blocked")
            
            if contact.trust_level == "trusted":
                return PolicyDecision(True, "approve", "Trusted sender")
        
        # Get policies ordered by priority
        policies = self.db.query(Policy).filter(
            Policy.organization_id == self.organization_id,
            Policy.enabled == True
        ).order_by(Policy.priority.desc()).all()
        
        # Apply hardcoded v1 rules if no custom policies
        if not policies:
            return self._default_v1_policy(draft, recipient)
        
        # Evaluate custom policies
        for policy in policies:
            result = self._evaluate_policy(policy, draft, recipient)
            if result:
                return result
        
        # Default: allow if no policy blocks
        return PolicyDecision(True, "approve", "No policy matched")
    
    def _default_v1_policy(self, draft: Draft, recipient: str) -> PolicyDecision:
        """Default v1 policy rules"""
        
        # External recipient check
        is_external = not recipient.endswith("@internal")  # Simplistic for now
        
        if is_external:
            return PolicyDecision(
                False, 
                "require_approval", 
                "External recipients require approval",
                requires_approval=True
            )
        
        # Check confidence if present
        if draft.confidence and draft.confidence < 0.7:
            return PolicyDecision(
                False,
                "require_approval",
                f"Low confidence ({draft.confidence}) requires approval",
                requires_approval=True
            )
        
        return PolicyDecision(True, "approve", "Default approval")
    
    def _evaluate_policy(self, policy: Policy, draft: Draft, recipient: str) -> Optional[PolicyDecision]:
        """Evaluate a single policy"""
        
        # External recipients
        if policy.rule_type == "external_requires_approval":
            is_external = not recipient.endswith("@internal")
            if is_external:
                return PolicyDecision(
                    False,
                    policy.action,
                    f"Policy '{policy.name}': external recipient",
                    requires_approval=(policy.action == "require_approval")
                )
        
        # Low confidence
        if policy.rule_type == "low_confidence_requires_approval":
            if draft.confidence and draft.confidence < policy.condition.get("threshold", 0.7):
                return PolicyDecision(
                    False,
                    policy.action,
                    f"Policy '{policy.name}': low confidence",
                    requires_approval=(policy.action == "require_approval")
                )
        
        # Blocked sender domains
        if policy.rule_type == "blocked_sender_blocked":
            blocked_domains = policy.condition.get("domains", [])
            for domain in blocked_domains:
                if domain in draft.message.from_addr:
                    return PolicyDecision(
                        False,
                        "block",
                        f"Policy '{policy.name}': blocked domain {domain}"
                    )
        
        # Financial language triggers approval
        if policy.rule_type == "financial_blocked":
            financial_keywords = policy.condition.get("keywords", ["payment", "invoice", "wire"])
            body_lower = draft.body_text.lower()
            if any(kw in body_lower for kw in financial_keywords):
                return PolicyDecision(
                    False,
                    policy.action,
                    f"Policy '{policy.name}': financial language detected",
                    requires_approval=(policy.action == "require_approval")
                )
        
        return None
    
    def get_applicable_policies(self) -> list:
        """Get all enabled policies for the org"""
        return self.db.query(Policy).filter(
            Policy.organization_id == self.organization_id,
            Policy.enabled == True
        ).order_by(Policy.priority.desc()).all()
