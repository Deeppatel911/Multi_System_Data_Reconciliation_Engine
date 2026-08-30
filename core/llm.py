from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from core.schemas import UnifiedCustomerProfile

load_dotenv()

# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------
# We are no longer talking to Groq directly.
# We talk to our local LiteLLM Proxy on port 4000, which handles the routing.
# LiteLLM accepts any string for the API key when running locally.
structured_resolver_llm = ChatOpenAI(
    base_url="http://127.0.0.1:4000",
    api_key="sk-litellm-local",
    model="mdm-resolver",             # This matches the model_name in our YAML!
    temperature=0
)

# Force the model to emit a payload that validates directly against the
# UnifiedCustomerProfile schema (field names, types, and nesting included).
structured_resolver_llm = structured_resolver_llm.with_structured_output(UnifiedCustomerProfile)
