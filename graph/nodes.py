import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from graph.state import ReconciliationState
from typing import List, Dict, Any


async def _fetch_from_mcp(server_script: str, tool_name: str, query: str) -> List[Dict[str, Any]]:
    """Helper function to open an MCP session and call a specific tool."""
    server_params = StdioServerParameters(
        command="python",
        args=[server_script]
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments={"query": query})

                # FastMCP returns the JSON as a string inside the content object; we parse it back to a Python list
                return json.loads(result.content[0].text)
    except Exception as e:
        print(f"Error fetching from {server_script}: {e}")
        return []


async def fetch_all_data_node(state: ReconciliationState) -> dict:
    """LangGraph Node: Fetches data from all 3 MCP servers in parallel."""
    query = state["query"]
    print(f"\nFetching data in parallel for query: '{query}'...")

    # 1. Dispatch all three tasks simultaneously
    crm_task = _fetch_from_mcp("mcp_servers/crm.py", "search_crm_records", query)
    billing_task = _fetch_from_mcp("mcp_servers/billing.py", "search_billing_records", query)
    app_db_task = _fetch_from_mcp("mcp_servers/app_db.py", "search_app_db", query)

    # 2. Await them all together
    crm_res, billing_res, app_db_res = await asyncio.gather(crm_task, billing_task, app_db_task)

    print("Parallel data extraction complete.")

    # 3. Return the payload to update the LangGraph state
    return {
        "crm_data": crm_res,
        "billing_data": billing_res,
        "app_db_data": app_db_res
    }


async def persist_node(state: ReconciliationState) -> dict:
    """LangGraph Node: Persists the resolved canonical profile to the internal app DB."""
    canonical_profile = state["canonical_profile"]

    # canonical_profile may be a Pydantic model (UnifiedCustomerProfile) or already a plain dict
    if hasattr(canonical_profile, "model_dump"):
        profile_dict = canonical_profile.model_dump()
    else:
        profile_dict = canonical_profile

    server_params = StdioServerParameters(
        command="python",
        args=["mcp_servers/app_db.py"]
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "save_canonical_profile",
                    arguments={"profile": profile_dict}
                )
                response = json.loads(result.content[0].text)
                print(f"Canonical profile saved successfully: {response}")
    except Exception as e:
        print(f"Error persisting canonical profile: {e}")

    # No state updates are needed after saving
    return {}


async def approval_node(state: ReconciliationState) -> dict:
    """LangGraph Node: Resumes execution after a human has approved the profile."""
    print("Human approval received! Resuming execution...")
    return {}
