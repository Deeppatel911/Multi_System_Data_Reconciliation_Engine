import json
import asyncio
from fastapi import FastAPI, Request, BackgroundTasks
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from graph.builder import graph_builder

app = FastAPI()


async def resume_graph(decision: str):
    """Background task to wake up LangGraph and resume execution."""
    # 1. Re-open the specific state database
    async with AsyncSqliteSaver.from_conn_string("state.db") as memory:
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
