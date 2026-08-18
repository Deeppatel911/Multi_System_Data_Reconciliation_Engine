from fastmcp import FastMCP
from typing import List, Dict, Any

mcp = FastMCP("Stripe_Billing")

MOCK_BILLING_DATA = [
    {
        "stripe_id": "cus_A123",
        "legal_name": "Acme Corporation LLC",
        "billing_email": "finance@acme.io",
        "monthly_recurring_revenue": 5000
    },
    {
        "stripe_id": "cus_B456",
        "legal_name": "Globex Inc.",
        "billing_email": "billing@globex.io",
        "monthly_recurring_revenue": 200
    }
]

@mcp.tool
def search_billing_records(query: str) -> List[Dict[str, Any]]:
    """Search Stripe billing records by company legal name or billing email."""
    query = query.lower()
    return [
        record for record in MOCK_BILLING_DATA
        if query in record["legal_name"].lower() or query in record["billing_email"].lower()
    ]

if __name__ == "__main__":
    mcp.run()
