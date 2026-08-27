import json
import os


def create_test_case(test_id, category, query, crm, billing, app_db, expected_merge, expected_discrepancies,
                     expected_human_review):
    return {
        "test_id": test_id,
        "category": category,
        "query": query,
        "inputs": {
            "crm_data": crm,
            "billing_data": billing,
            "app_db_data": app_db
        },
        "expected_behavior": {
            "should_merge": expected_merge,
            "expected_discrepancy_count": expected_discrepancies,
            "requires_human_approval": expected_human_review
        }
    }


def generate_benchmark_dataset():
    test_cases = []

    # ==========================================
    # CATEGORY 1: Clean Matches (Test Cases 1-8)
    # ==========================================
    # Perfect alignment across all 3 systems.
    for i in range(1, 9):
        test_cases.append(create_test_case(
            test_id=f"TC_{i:03d}_CLEAN",
            category="clean_match",
            query=f"company_{i}",
            crm=[{"id": f"crm_{i}", "name": f"Company {i} Inc", "domain": f"company{i}.com", "tier": "Enterprise"}],
            billing=[{"id": f"bil_{i}", "name": f"Company {i} Inc", "email": f"billing@company{i}.com"}],
            app_db=[{"id": f"app_{i}", "name": f"Company {i} Inc", "status": "active"}],
            expected_merge=True,
            expected_discrepancies=0,
            expected_human_review=False
        ))

    # ==========================================
    # CATEGORY 2: Edge Cases / Discrepancies (Test Cases 9-17)
    # ==========================================
    # Slight variations, missing data, or conflicting fields.
    for i in range(9, 18):
        # Introduce a legal suffix mismatch and a missing email
        test_cases.append(create_test_case(
            test_id=f"TC_{i:03d}_EDGE",
            category="edge_case_discrepancy",
            query=f"startup_{i}",
            crm=[{"id": f"crm_{i}", "name": f"Startup {i}", "domain": f"startup{i}.io", "tier": "Pro"}],
            billing=[{"id": f"bil_{i}", "name": f"Startup {i} LLC", "email": None}],  # Missing email, added LLC
            app_db=[{"id": f"app_{i}", "name": f"Startup {i}", "status": "active"}],
            expected_merge=True,
            expected_discrepancies=2,  # Name suffix mismatch, missing email
            expected_human_review=True  # Discrepancies should trigger HITL
        ))

    # ==========================================
    # CATEGORY 3: Distinct Entities / Traps (Test Cases 18-25)
    # ==========================================
    # Similar names but clearly different companies (e.g., different domains/regions)
    for i in range(18, 26):
        test_cases.append(create_test_case(
            test_id=f"TC_{i:03d}_TRAP",
            category="distinct_entities",
            query=f"global_tech_{i}",
            # US Branch
            crm=[{"id": f"crm_{i}a", "name": f"Global Tech {i}", "domain": f"globaltech{i}.com", "tier": "Enterprise"}],
            # UK Branch (Different domain, different email)
            billing=[{"id": f"bil_{i}b", "name": f"Global Tech {i} Ltd", "email": f"finance@globaltech{i}.co.uk"}],
            # App DB shows the US branch
            app_db=[{"id": f"app_{i}a", "name": f"Global Tech {i}", "status": "active"}],
            expected_merge=False,  # The LLM should realize .com and .co.uk are distinct corporate entities
            expected_discrepancies=3,
            expected_human_review=True  # Low confidence should trigger HITL
        ))

    # Write to JSON fixture
    output_path = os.path.join(os.path.dirname(__file__), "benchmark_dataset.json")
    with open(output_path, "w") as f:
        json.dump(test_cases, f, indent=4)

    print(f"Successfully generated 25 benchmark test cases at: {output_path}")


if __name__ == "__main__":
    generate_benchmark_dataset()
