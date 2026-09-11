import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from graph.state import ReconciliationState

import os

# Import the tool functions directly, bypassing the stdio subprocess overhead
from mcp_servers.crm import search_crm_records
from mcp_servers.billing import search_billing_records
from mcp_servers.app_db import search_app_db, save_canonical_profile


async def fetch_all_data_node(state: ReconciliationState) -> dict:
    """LangGraph Node: Fetches data from all 3 MCP servers in parallel."""
    query = state["query"]
    print(f"\nFetching data in parallel for query: '{query}'...")

    # 1. Dispatch all three tasks simultaneously
    # CRM and Billing are synchronous functions, so we offload them to threads.
    # App DB is already async, so we await it directly.
    crm_task = asyncio.to_thread(search_crm_records, query)
    billing_task = asyncio.to_thread(search_billing_records, query)
    app_db_task = search_app_db(query)

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
        args=["mcp_servers/app_db.py"],
        env=dict(os.environ)
    )

    try:
        # Directly await the async database save function
        response = await save_canonical_profile(profile_dict)
        print(f"Canonical profile saved successfully: {response}")
    except Exception as e:
        print(f"Error persisting canonical profile: {e}")

    # No state updates are needed after saving
    return {}


async def approval_node(state: ReconciliationState) -> dict:
    """LangGraph Node: Resumes execution after a human has approved the profile."""
    print("Human approval received! Resuming execution...")
    return {}
