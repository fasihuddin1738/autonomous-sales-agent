"""
Central config for the outreach-pipeline module.
Load once, import everywhere. Keep hackathon-simple: env vars + sane defaults.
"""
import os
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # --- Email (Resend) ---
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "outreach@nexaflow.ai")
    EMAIL_REPLY_TO: str = os.getenv("EMAIL_REPLY_TO", "")

    # --- Follow-up timing ---
    FOLLOW_UP_DELAY_DAYS: int = int(os.getenv("FOLLOW_UP_DELAY_DAYS", "3"))
    MAX_FOLLOW_UPS: int = int(os.getenv("MAX_FOLLOW_UPS", "1"))  # Day 0 + 1 follow-up per spec

    # --- Meeting briefing ---
    BRIEFING_LEAD_TIME_MIN: int = int(os.getenv("BRIEFING_LEAD_TIME_MIN", "30"))

    # --- Storage ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./nexaflow_pipeline.db")

    # --- LLM (for email generation / classification) ---
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "claude-sonnet-4-6")


settings = Settings()
