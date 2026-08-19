import asyncio
from graph.state import ReconciliationState
from graph.nodes import fetch_all_data_node


async def main():
    # 1. Initialize the starting state
    initial_state = ReconciliationState(
        query="acme",
        crm_data=[],
        billing_data=[],
        app_db_data=[],
        canonical_profile=None,
        discrepancies=[],
        human_approval_required=False
    )

    # 2. Run the node
    updated_state = await fetch_all_data_node(initial_state)

    # 3. Print the results
    print("\n--- State Updates Received ---")
    print(f"CRM Records Found: {len(updated_state['crm_data'])}")
    print(f"Billing Records Found: {len(updated_state['billing_data'])}")
    print(f"App DB Records Found: {len(updated_state['app_db_data'])}")

    print("\nRaw CRM Data Snapshot:")
    print(updated_state['crm_data'])


if __name__ == "__main__":
    asyncio.run(main())
