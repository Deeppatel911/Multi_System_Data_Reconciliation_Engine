import time
import os
import json
import pytest
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langfuse.langchain import CallbackHandler
from langfuse import get_client

# Import our actual open-source worker chain to test it!
from graph.resolver import resolution_chain

# ---------------------------------------------------------
# 1. Load the Golden Dataset
# ---------------------------------------------------------
DATASET_PATH = os.path.join(os.path.dirname(__file__), "benchmark_dataset.json")
with open(DATASET_PATH, "r") as f:
    TEST_CASES = json.load(f)


# ---------------------------------------------------------
# 2. Define the GPT-4o Judge
# ---------------------------------------------------------
class EvalRubric(BaseModel):
    hallucinated: bool = Field(
        description="True if the canonical profile contains fabricated data NOT present in the raw inputs.")
    well_calibrated: bool = Field(
        description="True if the confidence score logically matches the severity of the discrepancies found.")
    judge_reasoning: str = Field(description="A 1-sentence explanation of the grade.")


# We use GPT-4o with temperature 0 for strict, deterministic grading
judge_llm = ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(EvalRubric)

JUDGE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are an expert AI Evaluator grading an entity resolution model. Strictly evaluate the actual output against the raw inputs."
     "CRITICAL: The worker model is instructed to map the input 'crm_data' to the key 'salesforce', and 'billing_data' to the key 'stripe'. "
     "Do NOT flag the words 'salesforce', 'stripe', or 'app_db' as hallucinations. Only flag if the actual entity values (emails, names, domains) are fabricated."
     ),

    ("human", """
    RAW INPUTS (CRM, Billing, App DB):
    {inputs}

    WORKER LLM OUTPUT (Canonical Profile & Discrepancies):
    {output}

    Evaluate for hallucination and confidence calibration.
    """)
])

judge_chain = JUDGE_PROMPT | judge_llm


# ---------------------------------------------------------
# 3. The Pytest Execution Loop
# ---------------------------------------------------------
@pytest.mark.parametrize("test_case", TEST_CASES, ids=[tc["test_id"] for tc in TEST_CASES])
def test_entity_resolution(test_case):
    """Runs the open-source resolver against a test case and grades the result."""

    print(f"\nEvaluating: {test_case['test_id']}...")

    # Prevent hitting API rate limits on free tiers
    time.sleep(3)

    # Initialize Langfuse Handler per test case
    langfuse_handler = CallbackHandler()

    # Extract test inputs
    inputs = test_case["inputs"]
    expected = test_case["expected_behavior"]

    # 1. RUN THE WORKER MODEL (The model we are evaluating)
    # We pass the JSON data as formatted strings, exactly how the LangGraph node does it
    actual_profile = resolution_chain.invoke({
        "query": test_case["query"],
        "crm_data": json.dumps(inputs["crm_data"]),
        "billing_data": json.dumps(inputs["billing_data"]),
        "app_db_data": json.dumps(inputs["app_db_data"]),
    },
        config={"callbacks": [langfuse_handler]})

    print("\n--- WHAT THE LLM ACTUALLY OUTPUT ---")
    print(actual_profile.model_dump_json(indent=2))
    print("------------------------------------")

    # 2. DETERMINISTIC ASSERTS (Hard Math & Logic)
    # Did it flag the correct number of discrepancies?
    actual_discrepancy_count = len(actual_profile.discrepancies)
    assert actual_discrepancy_count == expected["expected_discrepancy_count"], \
        f"Failed Discrepancy Count. Expected {expected['expected_discrepancy_count']}, got {actual_discrepancy_count}"

    # Would this have bypassed human approval? (Confidence >= 0.85 and 0 discrepancies)
    requires_human_approval = (actual_profile.confidence_metrics.score < 0.85 or actual_discrepancy_count > 0)
    assert requires_human_approval == expected["requires_human_approval"], \
        f"Failed Routing Logic. Expected HITL={expected['requires_human_approval']}, got {requires_human_approval}"

    # 3. LLM-AS-A-JUDGE ASSERTS (Nuance & Safety)
    # Ask GPT-4o to grade the worker model's output
    judge_grade = judge_chain.invoke({
        "inputs": json.dumps(inputs, indent=2),
        "output": actual_profile.model_dump_json(indent=2)
    })

    print(f"  -> Judge Score: Hallucinated={judge_grade.hallucinated}, Calibrated={judge_grade.well_calibrated}")
    print(f"  -> Judge Reasoning: {judge_grade.judge_reasoning}")

    # Ensure traces flush over the network before test completion
    # langfuse_handler.flush()
    get_client().flush()

    # Assert the judge gave it a passing grade
    assert judge_grade.hallucinated is False, "Judge detected hallucinated data!"
    assert judge_grade.well_calibrated is True, "Judge detected poor confidence calibration!"
