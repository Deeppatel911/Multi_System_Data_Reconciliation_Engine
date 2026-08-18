from fastmcp import FastMCP
from typing import List, Dict, Any

# 1. Initialize the FastMCP Server
mcp = FastMCP("Salesforce_CRM")

# 2. Mock Database with messy, unstructured data
MOCK_CRM_DATA = [
    {
        "crm_id": "sf_001",
        "company_name": "Acme Corp",
        "website": "acme-corp.com",
        "tier": "Enterprise",
        "primary_contact": "john.doe@acme.com"
    },
    {
        "crm_id": "sf_002",
        "company_name": "Globex",
        "website": "globex.io",
        "tier": "Startup",
        "primary_contact": "admin@globex.io"
    }
]

# 3. Expose the Tool using the decorator
@mcp.tool
def search_crm_records(query: str) -> List[Dict[str, Any]]:
    """Search Salesforce CRM records by company name or website domain."""
    query = query.lower()
    return [
        record for record in MOCK_CRM_DATA
        if query in record["company_name"].lower() or query in record["website"].lower()
    ]

if __name__ == "__main__":
    mcp.run()
