# AgentHack — Autonomous Sales Agent

An end-to-end autonomous outbound sales pipeline featuring ICP discovery, deep company research, qualification scoring, personalized outreach generation, multi-provider email dispatch, automated follow-ups, reply classification, and meeting briefings.

---

## 🏗️ Architecture & Modules

1. **Discovery & ICP** (`discovery/`, `api/discovery.py`)
   - ICP definition, directory scrapers, filtering, search, and rate limiting.
2. **Deep Research & Qualification** (`research/`, `qualification/`)
   - Live & mock search client (Tavily/Serper), LLM fact extraction, qualification scoring, and decision-maker identification.
3. **Outreach & Execution Pipeline** (`outreach/`, `pipeline/`, `api/routes.py`, `dashboard/`)
   - Evidence-grounded email generation, dual-channel dispatch (Gmail SMTP + Resend), deterministic follow-up state machine, response classifier, meeting scheduler, and Streamlit kanban dashboard.
4. **RAG & Knowledge** (`rag/`)
   - Document ingest, chunking, and ChromaDB vector store retrieval for company service matching.

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env

# 3. Run FastAPI Backend
uvicorn main:app --reload

# 4. (Optional) Run Streamlit Pipeline Kanban Dashboard
streamlit run dashboard/app.py
```

---

## 🧪 Testing

```bash
# Run outreach pipeline tests
pytest tests/ -q

# Run research smoke test
python -m tests.test_deep_research
```
