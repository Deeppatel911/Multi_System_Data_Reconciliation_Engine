from typing import TypedDict, List, Dict, Any, Optional
from core.schemas import UnifiedCustomerProfile, DiscrepancyReport


class ReconciliationState(TypedDict):
    """
    The shared memory object for the LangGraph workflow.
    Every node reads from and updates this state.
    """
    query: str

    # Raw data extracted from the MCP servers
    crm_data: List[Dict[str, Any]]
    billing_data: List[Dict[str, Any]]
    app_db_data: List[Dict[str, Any]]

    # Final outputs (To be populated in Days 4 & 5)
    canonical_profile: Optional[UnifiedCustomerProfile]
    discrepancies: List[DiscrepancyReport]

    # Control flags
    human_approval_required: bool
