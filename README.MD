# Multi-System Data Reconciliation Engine

An enterprise-grade, stateful AI agent built with **LangGraph** and the **Model Context Protocol (MCP)** that performs probabilistic semantic entity resolution across disparate SaaS systems (CRM, Billing, and Internal App DBs) with automated Human-in-the-Loop (HITL) exception handling.

---

## Tech Stack

* **Orchestration:** LangGraph, LangChain Core
* **Tool Abstraction:** Model Context Protocol (FastMCP Python SDK)
* **LLM Engine:** Groq (`openai/gpt-oss-120b`), OpenAI (`gpt-4o`)
* **State Persistence:** SQLite / PostgreSQL Checkpointers (`AsyncSqliteSaver`)
* **Observability:** Langfuse SDK
* **Data Validation:** Pydantic V2

---

## Directory Structure

```text
multi-system_data_reconciliation_engine/
├── .env                     # Environment variables & API keys
├── requirements.txt         # Project dependencies
├── README.md                # Project documentation
├── mcp_servers/             # FastMCP Data Microservices
│   ├── crm.py               # Salesforce Mock MCP Server
│   ├── billing.py           # Stripe Mock MCP Server
│   └── app_db.py            # PostgreSQL Mock MCP Server
├── graph/                   # LangGraph State Machine
│   ├── state.py             # TypedDict state definitions
│   ├── nodes.py             # Graph execution nodes
│   ├── edges.py             # Conditional routing logic
│   └── builder.py           # StateGraph compiler
├── core/                    # Shared Schemas & LLM Setup
│   ├── schemas.py           # Pydantic data contracts
│   └── llm.py               # Inference clients
└── main.py                  # Pipeline execution entry point

