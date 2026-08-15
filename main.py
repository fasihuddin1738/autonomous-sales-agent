"""
main.py — project root

Creates the single shared FastAPI app and wires in each branch's router.
Each teammate owns one router file under /api and adds ONE line here
(the include_router call) — nobody edits another person's router file.

Run with:
    uvicorn main:app --reload

Then open http://127.0.0.1:8000/docs for the interactive Swagger UI.
"""

from fastapi import FastAPI

from api.discovery import router as discovery_router
from api.routes import router as outreach_router
from api.research_qualify import router as research_router

app = FastAPI(title="AgentHack — Autonomous Sales Agent API")
app.include_router(research_router, prefix="/research", tags=["Research & Qualification"])

app.include_router(discovery_router)
app.include_router(outreach_router, prefix="/outreach", tags=["Outreach & Pipeline"])


@app.get("/health")
def health():
    return {"status": "ok"}
