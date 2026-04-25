"""
Tool: Order Lookup
Simulates a backend order system. Replace with a real API call in production.
"""

from typing import Optional, Dict


MOCK_ORDERS: Dict[str, Dict] = {
    "ORD-1001": {
        "id": "ORD-1001",
        "customer": "alice@example.com",
        "items": [{"sku": "SHIRT-BLU-M", "qty": 2, "price": 29.99}],
        "total": 59.98,
        "status": "shipped",
        "tracking": "1Z999AA10123456784",
        "carrier": "UPS",
        "shipped_at": "2026-04-14T10:30:00Z",
        "estimated_delivery": "2026-04-18",
    },
    "ORD-1002": {
        "id": "ORD-1002",
        "customer": "bob@example.com",
        "items": [{"sku": "BOOK-SCIFI-01", "qty": 1, "price": 14.99}],
        "total": 14.99,
        "status": "processing",
        "tracking": None,
        "shipped_at": None,
        "estimated_delivery": "2026-04-22",
    },
    "ORD-1003": {
        "id": "ORD-1003",
        "customer": "carol@example.com",
        "items": [{"sku": "CABLE-USB-C", "qty": 3, "price": 9.99}],
        "total": 29.97,
        "status": "delivered",
        "tracking": "1Z999AA10123456799",
        "carrier": "UPS",
        "shipped_at": "2026-04-10T08:15:00Z",
        "delivered_at": "2026-04-13T14:22:00Z",
    },
}


def lookup(order_id: str) -> Optional[Dict]:
    """Look up an order by ID. Returns None if not found."""
    return MOCK_ORDERS.get(order_id.upper())
