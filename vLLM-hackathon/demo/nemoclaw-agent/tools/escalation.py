"""
Tool: Escalation
Hands off the conversation to a human agent when the LLM decides it can't help.
"""

from typing import Dict
from datetime import datetime, timezone


def escalate(reason: str, customer_email: str, conversation_summary: str) -> Dict:
    """
    Escalate to a human support agent.

    The agent should call this when:
    - Customer is upset / asks for a human
    - Issue requires refund approval > $100
    - Agent has tried 3+ times and still can't resolve
    """
    return {
        "escalated": True,
        "customer": customer_email,
        "reason": reason,
        "summary": conversation_summary,
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "expected_response_time_minutes": 15,
    }
