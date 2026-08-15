"""
scripts/run_full_pipeline_api.py

Calls the live FastAPI server to run: discovery -> research/qualify batch.
Requires `uvicorn main:app --reload` running in another terminal first.

Run from project root:
    python scripts/run_full_pipeline_api.py
"""

import requests
import json

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

print("\n=== Testing outreach on the first qualified lead ===")
qualified_leads = [l for l in process_data["leads"] if l.get("qualification", {}).get("is_qualified")]

if not qualified_leads:
    print("No qualified leads to test outreach with.")
else:
    test_lead = qualified_leads[0]
    lead_id = test_lead["id"]
    print(f"Using lead: {test_lead['company_name']} (id={lead_id})")

    # 1. Draft an email
    print("\n--- Drafting email ---")
    draft_resp = requests.post(f"{BASE_URL}/outreach/leads/{lead_id}/draft-email", timeout=60)
    draft_resp.raise_for_status()
    draft_data = draft_resp.json()
    outreach_list = draft_data.get("outreach", [])
    if outreach_list:
        print(f"Drafted email subject: {outreach_list[-1].get('subject')}")
        print(f"Body preview: {outreach_list[-1].get('body', '')[:200]}...")
    else:
        print("No outreach message found after drafting — check the response:")
        print(json.dumps(draft_data, indent=2)[:1000])

# 2. Send it (dry run to avoid actually emailing anyone during testing)
    print("\n--- Sending email (check if dry_run is supported/default) ---")
    if outreach_list:
        outreach_message_id = outreach_list[-1].get("id")
        send_resp = requests.post(
            f"{BASE_URL}/outreach/leads/{lead_id}/send-email",
            json={"outreach_message_id": outreach_message_id, "dry_run": True},
            timeout=60,
        )
        print(f"Send status: {send_resp.status_code}")
        if send_resp.status_code == 200:
            print(json.dumps(send_resp.json().get("outreach", []), indent=2)[:500])
        else:
            print(f"Send response: {send_resp.text[:500]}")
    else:
        print("No drafted message to send.")

    print(f"\nCheck GET /outreach/leads/{lead_id} to see full outreach state.")
