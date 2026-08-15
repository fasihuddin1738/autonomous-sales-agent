"""
scripts/run_full_pipeline_api.py

Calls the live FastAPI server to run: discovery -> research/qualify batch.
Requires `uvicorn main:app --reload` running in another terminal first.

Run from project root:
    python scripts/run_full_pipeline_api.py
"""

import requests

BASE_URL = "http://127.0.0.1:8000"

icp = {
    "target_location": "Karachi, Pakistan",
    "target_industry": "real estate",
    "special_focus": "high inbound lead volume",
}

print("=== Calling /discovery/discover ===")
discover_resp = requests.post(
    f"{BASE_URL}/discovery/discover",
    json={**icp, "max_results_per_query": 3},
    timeout=900,  # 15 minutes — discovery + directory-mining can run long under rate limits
)
discover_resp.raise_for_status()
discover_data = discover_resp.json()
print(f"Discovered {discover_data['count']} leads.\n")

leads = discover_data["leads"]

print("=== Calling /research/process-batch ===")
process_resp = requests.post(
    f"{BASE_URL}/research/process-batch",
    json={"leads": leads, "icp": icp, "limit": 3},   # add this
    timeout=900,
)
process_resp.raise_for_status()
process_data = process_resp.json()

print(f"Processed: {process_data['processed']}")
print(f"Qualified: {process_data['qualified']}\n")

for lead in process_data["leads"]:
    q = lead.get("qualification") or {}
    print(f"- {lead['company_name']}: score={q.get('score')} "
          f"qualified={q.get('is_qualified')} "
          f"service={lead.get('recommended_service')}")

print("\nDone. Check GET /outreach/leads (or /docs) to see them in the pipeline.")
