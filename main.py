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
# from api.research import router as research_router        # teammate adds this
# from api.outreach import router as outreach_router          # fasihuddin adds this

app = FastAPI(title="AgentHack — Autonomous Sales Agent API")

app.include_router(discovery_router)
# app.include_router(research_router)
# app.include_router(outreach_router)


@app.get("/health")
def health():
    return {"status": "ok"}
