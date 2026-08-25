import asyncio
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from graph.builder import graph_builder
from utils.slack_notifier import send_discrepancy_alert


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
        # 1. THE INTERRUPTION FLAG
        # We tell the graph to freeze the moment it tries to enter the 'approval' node
        app = graph_builder.compile(
            checkpointer=memory,
            interrupt_before=["approval"]
        )

        print("\nGraph is running (Fetch -> Resolve -> Edge -> Persist/End)...")

        # 2. Run the graph
        final_state = await app.ainvoke(initial_state, config={"configurable": {"thread_id": "1"}})

        print("\nExecution Paused/Complete!")
        print(f"Confidence Score: {final_state['canonical_profile'].confidence_metrics.score}")
        print(f"Human Approval Required: {final_state.get('human_approval_required')}")

        if final_state.get('discrepancies'):
            print("\nDiscrepancy Details:")
            for disc in final_state['discrepancies']:
                print(f"  - Field [{disc.field_name}]: {disc.conflict_description}")
                print(f"    Values: {disc.conflicting_values}")

        # 3. Check if the graph is currently interrupted
        # get_state() looks inside state.db for the current status of thread "1"
        current_status = await app.aget_state({"configurable": {"thread_id": "1"}})

        # If the next node in the queue is 'approval', we know we are successfully frozen!
        if current_status.next == ('approval',):
            print("\nGraph execution suspended! Waiting for Human-in-the-Loop...")
            print("Current State Checkpoint Saved! Thread ID '1' safely stored in state.db.")

            # Fire the Slack alert because we are officially paused!
            send_discrepancy_alert(final_state, thread_id="1", channel="#new-channel")
        else:
            print("\nGraph routed to 'persist' node and saved the data to the DB!")

        print(f"\nFinal Profile Canonical ID: {final_state['canonical_profile'].canonical_id}")


if __name__ == "__main__":
    asyncio.run(main())
