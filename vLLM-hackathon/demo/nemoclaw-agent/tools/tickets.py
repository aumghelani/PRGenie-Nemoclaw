"""
Tool: Support Ticket Creation
Creates a ticket when the agent can't resolve the issue autonomously.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List

# In-memory ticket store for the demo. Replace with Zendesk/Jira/ServiceNow.
_TICKETS: List[Dict] = []


def create(
    subject: str,
    description: str,
    customer_email: str,
    priority: str = "normal",
) -> Dict:
    """
    Create a support ticket.

    Args:
        subject: One-line summary of the issue
        description: Full context — include order IDs, error messages, etc.
        customer_email: Customer contact
        priority: "low" | "normal" | "high" | "urgent"
    """
    if priority not in {"low", "normal", "high", "urgent"}:
        priority = "normal"

    ticket = {
        "id": f"TKT-{str(uuid.uuid4())[:8].upper()}",
        "subject": subject,
        "description": description,
        "customer": customer_email,
        "priority": priority,
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _TICKETS.append(ticket)
    return ticket


def list_all() -> List[Dict]:
    """Return all tickets — useful for eval/benchmarking."""
    return list(_TICKETS)
