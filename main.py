"""
Standalone entrypoint for testing this branch in isolation, before it's
merged/mounted into the team's main app. Run with:

    uvicorn main:app --reload

Then hit POST /outreach/debug/seed-mock-leads to populate some test leads,
and GET /outreach/leads to see them. Once merged, the team's main app should
import `router` from api/routes.py directly instead of using this file.
"""
from fastapi import FastAPI

from api.routes import router as outreach_router

app = FastAPI(title="NexaFlow Outreach Pipeline (standalone dev server)")
app.include_router(outreach_router, prefix="/outreach", tags=["outreach"])


@app.get("/health")
def health():
    return {"status": "ok"}
