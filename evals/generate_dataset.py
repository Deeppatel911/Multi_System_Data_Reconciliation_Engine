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
            crm=[{"crm_id": f"sf_{i:03d}", "company_name": f"Company {i} Inc", "website": f"company{i}.com",
                  "tier": "Enterprise", "primary_contact": f"admin@company{i}.com"}],
            billing=[{"stripe_id": f"cus_{i:03d}", "legal_name": f"Company {i} Inc",
                      "billing_email": f"finance@company{i}.com", "monthly_recurring_revenue": 5000}],
            app_db=[{"user_id": f"usr_{i:03d}", "company": f"Company {i} Inc", "email": f"admin@company{i}.com",
                     "is_active": True, "last_login": "2026-09-01"}],
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
            crm=[{"crm_id": f"sf_{i:03d}", "company_name": f"Startup {i}", "website": f"startup{i}.io",
                  "tier": "Startup", "primary_contact": f"founder@startup{i}.io"}],
            billing=[{"stripe_id": f"cus_{i:03d}", "legal_name": f"Startup {i} LLC", "billing_email": None,
                      "monthly_recurring_revenue": 1200}], # Missing email, added LLC
            app_db=[{"user_id": f"usr_{i:03d}", "company": f"Startup {i}", "email": f"founder@startup{i}.io",
                     "is_active": True, "last_login": "2026-09-05"}],
            expected_merge=True,
            expected_discrepancies=1,  # Name suffix mismatch, missing email
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
            crm=[{"crm_id": f"sf_{i:03d}a", "company_name": f"Global Tech {i}", "website": f"globaltech{i}.com",
                  "tier": "Enterprise", "primary_contact": f"admin@globaltech{i}.com"}],
            # UK Branch (Different domain, different email)
            billing=[{"stripe_id": f"cus_{i:03d}b", "legal_name": f"Global Tech {i} Ltd",
                      "billing_email": f"finance@globaltech{i}.co.uk", "monthly_recurring_revenue": 8500}],
            # App DB shows the US branch
            app_db=[{"user_id": f"usr_{i:03d}a", "company": f"Global Tech {i}", "email": f"admin@globaltech{i}.com",
                     "is_active": True, "last_login": "2026-08-20"}],
            expected_merge=False,  # The LLM should realize .com and .co.uk are distinct corporate entities
            expected_discrepancies=2,
            expected_human_review=True  # Low confidence should trigger HITL
        ))

    # Write to JSON fixture
    output_path = os.path.join(os.path.dirname(__file__), "benchmark_dataset.json")
    with open(output_path, "w") as f:
        json.dump(test_cases, f, indent=4)

    print(f"Successfully generated 25 benchmark test cases at: {output_path}")


if __name__ == "__main__":
    generate_benchmark_dataset()
