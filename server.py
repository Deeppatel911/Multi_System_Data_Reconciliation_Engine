import json
from fastapi import FastAPI, Request, BackgroundTasks
from graph.builder import graph_builder

import os
from dotenv import load_dotenv
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from pydantic import BaseModel
from utils.slack_notifier import send_discrepancy_alert

load_dotenv()
app = FastAPI()

# Dynamic Database URL Constructor for AWS RDS vs Local
DB_HOST = os.environ.get("DATABASE_HOST")

if DB_HOST:  # If this exists, we are running in the AWS Cloud
    DB_USER = os.environ.get("DATABASE_USER")
    DB_PASS = os.environ.get("DATABASE_PASSWORD")
    DB_PORT = os.environ.get("DATABASE_PORT", "5432")
    DB_NAME = os.environ.get("DATABASE_NAME", "mdm_db")
    LANGGRAPH_DB_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:  # Fall back to local .env for local testing
    LANGGRAPH_DB_URL = os.environ.get("LANGGRAPH_DB_URL")


# ---------------------------------------------------------
# NEW: Request Schema for Swagger UI
# ---------------------------------------------------------
class ReconcileRequest(BaseModel):
    query: str
    thread_id: str = "1"  # Defaulting to 1 to match your resume_graph hardcoding


# ---------------------------------------------------------
# NEW: The End-to-End Trigger Endpoint
# ---------------------------------------------------------
@app.post("/reconcile")
async def start_reconciliation(req: ReconcileRequest):
    """Kicks off the LangGraph execution in production."""
    print(f"\nStarting reconciliation for query: '{req.query}' (Thread: {req.thread_id})")

    async with AsyncPostgresSaver.from_conn_string(LANGGRAPH_DB_URL) as memory:
        await memory.setup()

        # Compile the graph and tell it to pause before human approval
        engine = graph_builder.compile(
            checkpointer=memory,
            interrupt_before=["approval"]
        )

        initial_state = {
            "query": req.query,
            "crm_data": [],
            "billing_data": [],
            "app_db_data": [],
            "canonical_profile": None,
            "discrepancies": [],
            "human_approval_required": False
        }

        config = {"configurable": {"thread_id": req.thread_id}}

        # Run the graph
        final_state = await engine.ainvoke(initial_state, config=config)
        current_status = await engine.aget_state(config)

        # If it paused at the approval node, fire the Slack alert
        if current_status.next == ('approval',):
            print("\nGraph paused at 'approval'. Firing Slack alert...")
            send_discrepancy_alert(final_state, thread_id=req.thread_id, channel="#new-channel")

            return {
                "status": "paused_for_review",
                "message": "Discrepancies found. Sent to Slack for Human-in-the-Loop approval.",
                "confidence_score": final_state['canonical_profile'].confidence_metrics.score
            }

        # If it bypassed approval (clean match), it went straight to persist
        return {
            "status": "completed",
            "message": "High confidence match. Data persisted to DB automatically.",
            "canonical_id": final_state['canonical_profile'].canonical_id
        }


async def resume_graph(decision: str):
    """Background task to wake up LangGraph and resume execution."""
    # 1. Connect to the Async Postgres checkpointer
    async with AsyncPostgresSaver.from_conn_string(LANGGRAPH_DB_URL) as memory:
        # IMPORTANT: Initialize the Postgres checkpoint tables if they don't exist
        await memory.setup()

        # 2. Recompile the graph engine
        engine = graph_builder.compile(checkpointer=memory)
        config = {"configurable": {"thread_id": "1"}}

        if decision == "approve":
            print("\nWebhook received APPROVE. Resuming graph to persist data...")

            # 3. Update the frozen state to indicate the human approved it
            await engine.aupdate_state(
                config,
                {"human_approval_required": False},
                as_node="approval"
            )

            # 4. Invoke with 'None' to tell LangGraph to just continue where it left off
            await engine.ainvoke(None, config=config)
            print("Graph execution complete. Canonical profile saved to App DB!")

        elif decision == "reject":
            print("\nWebhook received REJECT. Execution halted. Profile will not be saved.")
            # By doing nothing here, the graph remains safely suspended and won't hit the persist node.


@app.get("/")
def health_check():
    return {"status": "healthy", "service": "data-reconciliation-engine"}


@app.post("/slack/actions")
async def slack_webhook(request: Request, background_tasks: BackgroundTasks):
    """Catcher's mitt for the Slack button clicks."""
    # Slack sends interactive payloads as form data, not standard JSON
    form_data = await request.form()
    payload = json.loads(form_data.get("payload"))

    # Verify this is a button click action
    if payload.get("type") == "block_actions":
        action = payload["actions"][0]
        action_id = action.get("action_id")
        value = action.get("value")  # This will be "approve" or "reject"

        user = payload.get("user", {}).get("username", "Unknown User")
        print(f"\nIncoming Action: {user} clicked '{action_id}'")

        # Pass the decision to the LangGraph engine in the background
        background_tasks.add_task(resume_graph, value)

    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
