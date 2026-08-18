from fastmcp import FastMCP
from typing import List, Dict, Any

mcp = FastMCP("Internal_App_DB")

MOCK_DB_DATA = [
    {
        "user_id": "usr_98124",
        "company": "Acme",
        "email": "admin@acme.io",
        "is_active": False,
        "last_login": "2026-07-10"
    },
    {
        "user_id": "usr_77211",
        "company": "Globex",
        "email": "admin@globex.io",
        "is_active": True,
        "last_login": "2026-08-16"
    }
]

@mcp.tool
def search_app_db(query: str) -> List[Dict[str, Any]]:
    """Search PostgreSQL internal database records by company name or user email."""
    query = query.lower()
    return [
        record for record in MOCK_DB_DATA
        if query in record["company"].lower() or query in record["email"].lower()
    ]

if __name__ == "__main__":
    mcp.run()
