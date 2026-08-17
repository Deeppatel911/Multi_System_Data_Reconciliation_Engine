import os
from dotenv import load_dotenv
from langfuse import observe, get_client

# Load the environment variables (API Keys)
load_dotenv()


@observe()
def verify_pydantic_schemas():
    # This automatically becomes a nested span!
    return "Schemas validated successfully"


@observe()
def test_telemetry():
    print("Testing Langfuse connection...")

    # Call the child function
    result = verify_pydantic_schemas()
    print(f"Result: {result}")

    # Force flush the events to the Langfuse Cloud before the script exits
    get_client().flush()


if __name__ == "__main__":
    test_telemetry()
    print("Trace successfully dispatched! Check your Langfuse dashboard under 'Tracing'.")