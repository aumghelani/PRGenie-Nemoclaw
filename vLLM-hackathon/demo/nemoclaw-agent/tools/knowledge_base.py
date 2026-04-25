"""
Tool: Knowledge Base Search
Simulates a retrieval call against a product documentation corpus.
In production this would hit a vector DB (Chroma, Milvus, etc).
"""

from typing import List, Dict


# Mock product knowledge base for the demo.
# Attendees can replace this with their own docs + embedding retrieval.
KB_ENTRIES: List[Dict[str, str]] = [
    {
        "id": "kb-001",
        "title": "How to reset your password",
        "content": "Visit /account/reset and enter the email tied to your account. "
                   "You will receive a reset link within 5 minutes. The link expires in 24h.",
    },
    {
        "id": "kb-002",
        "title": "Shipping times and tracking",
        "content": "Standard shipping is 3-5 business days. Express is 1-2 days. "
                   "Track your order at /orders/{order_id} or via the email confirmation.",
    },
    {
        "id": "kb-003",
        "title": "Return policy",
        "content": "Returns are accepted within 30 days of delivery. "
                   "Items must be unworn and in original packaging. "
                   "Initiate a return from the order page; refunds process within 7 days.",
    },
    {
        "id": "kb-004",
        "title": "Subscription management",
        "content": "Manage your subscription at /account/subscriptions. "
                   "Cancel anytime; no cancellation fee. Refunds are prorated.",
    },
    {
        "id": "kb-005",
        "title": "International shipping",
        "content": "We ship to 45 countries. Customs and duties are the buyer's responsibility. "
                   "Delivery times vary: 7-14 business days for most regions.",
    },
]


def search(query: str, limit: int = 3) -> List[Dict[str, str]]:
    """
    Search the knowledge base.

    Naive keyword match — in production use semantic search with an embedding
    model served by vLLM or a dedicated embedding backend.
    """
    query_terms = [t.lower() for t in query.split() if len(t) > 2]
    scored = []
    for entry in KB_ENTRIES:
        blob = (entry["title"] + " " + entry["content"]).lower()
        score = sum(1 for term in query_terms if term in blob)
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda x: -x[0])
    return [entry for _, entry in scored[:limit]]
