"""
graph/resolver.py

LangGraph node responsible for LLM-driven entity resolution.

This module takes the raw, unmerged records pulled from the three MCP
sources (CRM, Billing, App DB) and asks an LLM to act as a strict Master
Data Management (MDM) / Data Reconciliation Engine: it must fuzzy-match the
records to a single real-world customer, canonicalize every field, flag
every discrepancy it finds, and emit a confidence-scored
`UnifiedCustomerProfile` that conforms exactly to the Pydantic contract in
`core/schemas.py`.
"""

import os

# Clear any invalid SSL_CERT_FILE injected by Git Bash before httpx initializes
if "SSL_CERT_FILE" in os.environ and not os.path.exists(os.environ["SSL_CERT_FILE"]):
    del os.environ["SSL_CERT_FILE"]

import json
import uuid

from langchain_core.prompts import ChatPromptTemplate
from langfuse.langchain import CallbackHandler

from core.schemas import UnifiedCustomerProfile
from graph.state import ReconciliationState

from graph.prompts import RESOLUTION_SYSTEM_PROMPT, RESOLUTION_HUMAN_PROMPT
from core.llm import structured_resolver_llm


resolution_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", RESOLUTION_SYSTEM_PROMPT),
        ("human", RESOLUTION_HUMAN_PROMPT),
    ]
)

resolution_chain = resolution_prompt | structured_resolver_llm


# ---------------------------------------------------------------------------
# LangGraph Node
# ---------------------------------------------------------------------------
def resolution_node(state: ReconciliationState) -> dict:
    """
    LangGraph Node: Fuses the raw crm_data / billing_data / app_db_data
    records in `state` into a single canonical UnifiedCustomerProfile via
    the LLM, and surfaces any detected discrepancies back into state.
    """
    query = state["query"]
    print(f"\nResolving canonical profile for query: '{query}'...")

    langfuse_handler = CallbackHandler()

    canonical_profile: UnifiedCustomerProfile = resolution_chain.invoke(
        {
            "query": query,
            "crm_data": json.dumps(state.get("crm_data", []), indent=2, default=str),
            "billing_data": json.dumps(state.get("billing_data", []), indent=2, default=str),
            "app_db_data": json.dumps(state.get("app_db_data", []), indent=2, default=str),
        },
        config={"callbacks": [langfuse_handler]},
    )

    # Guarantee canonical_id is always a genuinely new identifier even if the
    # model produced something non-unique or empty.
    if not canonical_profile.canonical_id:
        canonical_profile.canonical_id = str(uuid.uuid4())

    print(
        f"Resolution complete. confidence={canonical_profile.confidence_metrics.score:.2f} "
        f"discrepancies={len(canonical_profile.discrepancies)}"
    )

    # Route low-confidence merges to the human-in-the-loop review step.
    human_approval_required = (
        canonical_profile.confidence_metrics.score < 0.75
        or len(canonical_profile.discrepancies) > 0
    )

    return {
        "canonical_profile": canonical_profile,
        "discrepancies": canonical_profile.discrepancies,
        "human_approval_required": human_approval_required,
    }
