# Multi-System Data Reconciliation Engine

An enterprise-grade, stateful AI agent designed to perform probabilistic semantic entity resolution across disparate SaaS systems (CRM, Billing, and Internal App DBs). Built with **LangGraph** and the **Model Context Protocol (MCP)**, this engine fuses conflicting system records into a single canonical profile with automated Human-in-the-Loop (HITL) exception handling.

---

## Architecture & Tech Stack

- **Orchestration & API:** Python, FastAPI, LangGraph, FastMCP, SQLAlchemy.
- **AI & Data:** Amazon Bedrock (Claude Sonnet 5 primary, Llama 3.3 70B fallback, Mistral Large 3 for evaluations), PostgreSQL with `pgvector`, Amazon Titan Text Embeddings v2, LiteLLM proxy.
- **Cloud & DevOps:** AWS (ECS Fargate, RDS, ALB, ECR, CloudWatch, Secrets Manager, KMS), AWS CDK, Docker, GitHub Actions CI/CD.
- **Observability:** Langfuse Cloud.

### Execution Flow

```mermaid
flowchart LR
    A["POST /reconcile"] --> B["fetch<br/>CRM · Billing · App DB<br/>(parallel)"]
    B --> C["resolve<br/>LLM entity resolution"]
    C -->|"confidence ≥ 0.85<br/>and no discrepancies"| E["persist<br/>canonical profile → RDS"]
    C -->|"confidence < 0.85<br/>or discrepancies found"| D["approval<br/>graph suspended<br/>Slack alert sent"]
    D -->|"approved in Slack"| E
```

1. **Fetch:** Queries the Salesforce (CRM), Stripe (Billing), and internal App DB MCP tools concurrently.
2. **Resolve:** The resolver LLM fuses the records into a `UnifiedCustomerProfile` validated by Pydantic, with a confidence score and a list of discrepancies.
3. **Route:** Clean, high-confidence merges are persisted immediately. Anything with a confidence score below `0.85` or at least one discrepancy is suspended via a LangGraph interrupt, with state checkpointed to PostgreSQL.
4. **Approve:** A reviewer approves the merge from an interactive Slack message, which resumes the suspended thread and persists the golden record.

---

## Key Capabilities

- **Sub-6-Second Execution Latency:** Optimized from a distributed subprocess model to a high-performance modular monolith, utilizing `asyncio.to_thread` for concurrent MCP tool extraction to bypass stdio IPC overhead.
- **Dynamic HITL Concurrency:** Integrated an asynchronous Slack webhook to suspend LangGraph execution upon detecting low-confidence merges. The system parses dynamic thread states from Block Kit payloads to prevent database collisions during concurrent approvals.
- **Defense-in-Depth AWS Security:** Deployed via AWS CDK with compute in private subnets and PostgreSQL in isolated subnets with no internet route, KMS encryption at rest with automatic key rotation, runtime credential injection via AWS Secrets Manager, IAM permissions scoped to specific Bedrock model families, keyless container access through ECS Exec (SSM), and OIDC-based CI/CD with no long-lived AWS keys.
- **Automated CI/CD Evaluation Gate:** A Pytest harness in GitHub Actions runs the resolver against a 25-case golden dataset, deterministically asserting discrepancy detection and HITL routing, while Mistral Large 3 (a different model family from the resolver) grades every output for hallucination and confidence calibration. Deployment only proceeds if the evaluation job passes.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/reconcile` | Runs the reconciliation graph for a query. Body: `{"query": "...", "thread_id": "..."}`. Returns `completed` or `paused_for_review`. |
| `GET` | `/canonical` | Lists all persisted golden records. |
| `GET` | `/canonical/{company_name}` | Returns golden records matching a company name. |
| `POST` | `/slack/actions` | Slack interactivity webhook that resumes a suspended thread. |
| `GET` | `/` | Health check. |

Interactive documentation is available at `/docs` (Swagger UI).

---

## Evaluation Harness

The `evaluate` job in `.github/workflows/deploy.yml` runs `pytest evals/` against [`evals/benchmark_dataset.json`](evals/benchmark_dataset.json) before every deployment.

| Category | Cases | What it tests |
|---|---|---|
| Clean match | 8 | Consistent records that should merge automatically |
| Edge-case discrepancy | 9 | Conflicting fields that must be flagged and routed to HITL |
| Distinct entities (traps) | 8 | Look-alike records that must not be merged blindly |

Each case is scored in two layers:

1. **Deterministic assertions:** Were discrepancies detected when expected, and was the HITL routing decision correct?
2. **LLM-as-a-judge:** Mistral Large 3 checks the canonical profile for hallucinated data and verifies that the confidence score matches the severity of the discrepancies.

All runs are traced to Langfuse under a shared session for side-by-side review.

---

## Project Showcase

### 1. Slack Human-in-the-Loop (HITL) Interactivity

*Dynamic thread state parsing and approval routing via interactive Slack webhooks.*

![Slack HITL Approval Routing](docs/images/slack-hitl-interactivity.png)

### 2. Langfuse Observability & Tracing

*Full visibility into step-by-step LLM execution, token usage, and latency metrics.*

![Langfuse Trace Waterfall](docs/images/langfuse-trace-waterfall.png)

*Sub-6-second p90 execution latency tracked across the resolution graph.*

![Langfuse Latency Metrics](docs/images/langfuse-latency-metrics.png)

### 3. Automated CI/CD Pipeline (GitHub Actions)

*Strict Pytest evaluation gates ensuring discrepancy detection accuracy before deployment.*

![CI/CD Pipeline Success](docs/images/cicd-pipeline-success.png)

### 4. AWS ECS Fargate Deployment

*Zero-downtime rolling task replacements across private AWS subnets.*

![ECS Fargate Rolling Deployment](docs/images/ecs-fargate-deployment.png)

### 5. FastAPI Endpoints (Swagger UI)

*Triggering parallel MCP extractions and retrieving finalized canonical records.*

![Swagger UI - Reconcile Endpoint](docs/images/swagger-reconcile-endpoint.png)

![Swagger UI - Canonical Endpoint](docs/images/swagger-canonical-endpoint.png)

### 6. Webhook Execution Logs

*Real-time container logs demonstrating the non-blocking event loop resuming the frozen LangGraph thread.*

![FastAPI Webhook Logs](docs/images/fastapi-webhook-logs.png)

---

## Directory Structure

```text
multi-system_data_reconciliation_engine/
├── .github/workflows/     # CI/CD pipeline (evaluate → build → deploy)
├── core/                  # Shared schemas & LLM setup
├── evals/                 # Pytest evaluation harness & golden dataset
├── graph/                 # LangGraph state machine (nodes, edges, resolver)
├── infra/                 # AWS CDK infrastructure definition (VPC, ECS, RDS)
├── mcp_servers/           # Mock FastMCP microservices (CRM, Billing, App DB)
├── utils/                 # Slack notification webhooks
├── Dockerfile             # Single image running FastAPI + LiteLLM proxy
├── docker-compose.yml     # Local multi-container orchestration
├── litellm_config.yaml    # LLM routing and fallback chains
├── start.sh               # Container entrypoint (LiteLLM + Uvicorn)
└── server.py              # FastAPI webhook & LangGraph execution entry point
```

---

## How to Run & Deploy

### Prerequisites

- An AWS account with Amazon Bedrock model access enabled in `us-east-1` for Claude Sonnet 5, Llama 3.3 70B Instruct, Mistral Large 3, and Titan Text Embeddings v2.
- Python 3.11, Docker, and the AWS CDK CLI.
- A Slack app with a bot token (`chat:write` scope).
- A Langfuse Cloud project.

### 1. Configure AWS Secrets

Before deploying the infrastructure, create a secret in AWS Secrets Manager named `mdm/api-keys` containing the following JSON payload:

```json
{
  "LITELLM_API_KEY": "your_litellm_key",
  "SLACK_BOT_TOKEN": "xoxb-your-slack-bot-token",
  "LANGFUSE_SECRET_KEY": "sk-lf-...",
  "LANGFUSE_PUBLIC_KEY": "pk-lf-...",
  "LANGFUSE_HOST": "https://us.cloud.langfuse.com",
  "LANGFUSE_BASE_URL": "https://us.cloud.langfuse.com"
}
```

> **Note:** The ECS task definition reads every key above, so all of them must be present or the task will fail to start. Database credentials are generated automatically by CDK and don't belong in this secret.

### 2. Deploy AWS Infrastructure

Initialize and deploy the core AWS infrastructure (VPC, RDS PostgreSQL, ECR, ALB, and ECS Fargate cluster) using the AWS CDK:

```bash
cd infra
pip install -r requirements.txt
cdk bootstrap   # first time per account/region only
cdk synth
cdk deploy
```

> **Note:** Record the Application Load Balancer (ALB) URL from the stack outputs once the deployment completes.

### 3. Configure GitHub Actions

The pipeline authenticates to AWS through OIDC, so no long-lived AWS keys are stored in GitHub.

1. Create an IAM role named `GitHubActionsOIDCRole` that trusts GitHub's OIDC provider for this repository and allows pushing to ECR and updating the ECS service.
2. Add the following repository secrets: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`, `LANGFUSE_BASE_URL`, `LANGGRAPH_DB_URL`, `DATABASE_URL`, and `SLACK_BOT_TOKEN`.

### 4. Trigger CI/CD & Application Deployment

Push your code to the `main` branch to trigger the GitHub Actions workflow. The pipeline will automatically:

1. Run the Pytest evaluation harness against the golden dataset.
2. Build a single Docker image bundling the FastAPI server and the LiteLLM proxy.
3. Authenticate to AWS via OIDC and push the image to Amazon ECR.
4. Trigger a rolling update on the ECS Fargate service.

### 5. Configure Slack Interactivity

To enable the Human-in-the-Loop workflow:

1. Go to your **Slack App Dashboard → Interactivity & Shortcuts**.
2. Toggle **Interactivity** to **On**.
3. Set the **Request URL** to your ALB's endpoint: `http://<YOUR_ALB_DNS>/slack/actions`.
4. Invite the bot to the `#new-channel` channel, where discrepancy alerts are posted.
5. Trigger a reconciliation via `POST /reconcile` with an edge-case query to test the Slack approval routing.

### 6. Tear Down

To avoid ongoing AWS charges, destroy the stack when you're done:

```bash
cd infra
cdk destroy
```

---

## Future Roadmap

- **Semantic Candidate Blocking:** Embed stored App DB records with Amazon Titan at ingestion time so `pgvector` KNN retrieval returns the top-5 closest candidates, bounding the LLM context window as record volume grows.
- **RAG Pipeline Evaluation Suite:** Extend the CI harness with an ephemeral `pgvector` service container to measure retrieval quality (hit rate@5, MRR) against a seeded set of look-alike records, and add field-level discrepancy accuracy scoring against labeled ground truth.
- **Private Observability:** Deploy a self-hosted Langfuse v3 cluster natively within the AWS VPC using ClickHouse and ElastiCache to strictly isolate telemetry payloads from the public internet.

---

## License

This project is licensed under the [MIT License](LICENSE).
