import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

from core.schemas import UnifiedCustomerProfile

load_dotenv()

# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------
# `openai/gpt-oss-120b` is served via Groq's OpenAI-compatible open-weights
# lineup. temperature=0 keeps the reconciliation deterministic — this is a
# data-integrity task, not a creative one.
resolver_llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
    api_key=os.environ.get("GROQ_API_KEY"),
)

# Force the model to emit a payload that validates directly against the
# UnifiedCustomerProfile schema (field names, types, and nesting included).
structured_resolver_llm = resolver_llm.with_structured_output(UnifiedCustomerProfile)
