import asyncio
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from graph.builder import graph_builder


async def main():
    print("Starting Automated LangGraph Execution...")

    # 1. The starting clipboard
    initial_state = {
        "query": "acme",
        "crm_data": [],
        "billing_data": [],
        "app_db_data": [],
        "canonical_profile": None,
        "discrepancies": [],
        "human_approval_required": False
    }

    async with AsyncSqliteSaver.from_conn_string("state.db") as memory:
        app = graph_builder.compile(checkpointer=memory)

        # 2. Execute the entire graph autonomously
        print("\nGraph is running (Fetch -> Resolve -> Edge -> Persist/End)...")

        # We use ainvoke() because our fetch and persist nodes are async
        final_state = await app.ainvoke(initial_state, config={"configurable": {"thread_id": "1"}})

        # 3. Evaluate the routing outcome
        print("\nExecution Complete!")
        print(f"Confidence Score: {final_state['canonical_profile'].confidence_metrics.score}")
        print(f"Human Approval Required: {final_state.get('human_approval_required')}")

        if final_state.get('discrepancies'):
            print("\nDiscrepancy Details:")
            for disc in final_state['discrepancies']:
                print(f"  - Field [{disc.field_name}]: {disc.conflict_description}")
                print(f"    Values: {disc.conflicting_values}")

        if final_state.get('human_approval_required'):
            print("Graph routed to '__end__' due to discrepancies. (Persistence bypassed)")
        else:
            print("Graph routed to 'persist' node and saved the data to the DB!")

        print(f"\nFinal Profile Canonical ID: {final_state['canonical_profile'].canonical_id}")

        print(f"State Checkpoint Saved! Thread ID '1' safely stored in state.db for future resumption.")


if __name__ == "__main__":
    asyncio.run(main())
