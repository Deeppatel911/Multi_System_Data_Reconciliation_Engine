import asyncio
import json
from graph.nodes import fetch_all_data_node
from graph.resolver import resolution_node
from graph.state import ReconciliationState


async def main():
    print("Starting Day 4 End-to-End Node Pipeline Test...")

    # 1. Initialize starting state with query
    initial_state = ReconciliationState(
        query="acme",
        crm_data=[],
        billing_data=[],
        app_db_data=[],
        canonical_profile=None,
        discrepancies=[],
        human_approval_required=False
    )

    # 2. Run Step 1: Parallel extraction node
    print("\n--- Step 1: Parallel Data Extraction ---")
    extracted_state = await fetch_all_data_node(initial_state)

    # Merge extracted data into full state
    current_state: ReconciliationState = {
        **initial_state,
        **extracted_state
    }

    # 3. Run Step 2: Probabilistic Resolution Node (LLM via Groq)
    print("\n--- Step 2: LLM Probabilistic Entity Resolution ---")
    resolved_state = resolution_node(current_state)

    # 4. Inspect outputs
    profile = resolved_state["canonical_profile"]
    print("\n================= AUTHORITATIVE PROFILE =================")
    print(f"Canonical ID:      {profile.canonical_id}")
    print(f"Company Name:      {profile.company_name}")
    print(f"Domain:            {profile.domain}")
    print(f"Billing Email:     {profile.billing_email}")
    print(f"CRM Tier:          {profile.crm_tier}")
    print(f"Is Active:         {profile.is_active}")
    print(f"Confidence Score:  {profile.confidence_metrics.score}")
    print(f"Reasoning:         {profile.confidence_metrics.reasoning}")
    print(f"Human Required:    {resolved_state['human_approval_required']}")
    print(f"Discrepancies:     {len(resolved_state['discrepancies'])}")

    if resolved_state["discrepancies"]:
        print("\nDiscrepancy Details:")
        for disc in resolved_state["discrepancies"]:
            print(f"  - Field [{disc.field_name}]: {disc.conflict_description}")
            print(f"    Values: {disc.conflicting_values}")


if __name__ == "__main__":
    asyncio.run(main())
