import json
import os
from langfuse import Langfuse
from dotenv import load_dotenv

load_dotenv()

# ---- THE WINDOWS/CONDA BUG FIX ----
# Delete the broken Anaconda certificate path from Python's memory
os.environ.pop("SSL_CERT_FILE", None)
# -----------------------------------

# Initialize Langfuse client
langfuse = Langfuse()
dataset_name = "MDM-Reconciliation-Golden-Set"

print(f"Creating dataset: {dataset_name}...")
langfuse.create_dataset(
    name=dataset_name,
    description="25-case deterministic baseline for the MDM reconciliation engine"
)

# Load the benchmark JSON
DATASET_PATH = os.path.join(os.path.dirname(__file__), "benchmark_dataset.json")
with open(DATASET_PATH, "r") as f:
    test_cases = json.load(f)

# Upload each test case as a dataset item
print(f"Uploading {len(test_cases)} items...")
for tc in test_cases:
    langfuse.create_dataset_item(
        dataset_name=dataset_name,
        input=tc["inputs"],
        expected_output=tc["expected_behavior"],
        metadata={"category": tc["category"], "test_id": tc["test_id"]}
    )

print("Golden Dataset successfully uploaded to Langfuse!")
