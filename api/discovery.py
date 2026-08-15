"""
api/discovery.py

Discovery endpoints — owned by feature/rag-discovery.
Wraps discovery.pipeline.run_discovery().

This file only defines a router. The actual FastAPI app lives in the
project-root main.py, which includes this router. Don't create a
FastAPI() instance in here — that's what caused the "three apps"
problem we were avoiding.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from shared.schema import ICP
from discovery.pipeline import run_discovery

router = APIRouter(prefix="/discovery", tags=["discovery"])


class DiscoveryRequest(BaseModel):
    target_location: str
    target_industry: str
    company_size: str | None = None
    special_focus: str | None = None
    max_results_per_query: int = 8


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/discover")
def discover(req: DiscoveryRequest):
    """
    Builds an ICP from the request body and runs the full discovery
    pipeline (search -> cheap filter -> directory mining -> second
    filter -> dedup), returning the final list of Lead objects.
    """
    try:
        icp = ICP(
            target_location=req.target_location,
            target_industry=req.target_industry,
            company_size=req.company_size,
            special_focus=req.special_focus,
        )

        leads = run_discovery(
            icp,
            max_results_per_query=req.max_results_per_query,
        )

        return {
            "count": len(leads),
            "leads": [lead.model_dump() for lead in leads],
        }

    except Exception as e:
        # Discovery hits Tavily + Groq under the hood — surface the
        # real error instead of a bare 500 so it's debuggable live.
        raise HTTPException(status_code=500, detail=str(e))
