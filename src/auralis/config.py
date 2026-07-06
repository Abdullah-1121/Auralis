"""
Application settings — single source of truth for all configuration.

Everything comes from environment variables / .env. No module anywhere else
reads os.environ directly, and nothing here talks to the network — importing
config must never fail or block (lesson learned from the v0 prototype, which
authenticated to Google Sheets at import time).
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Strip surrounding whitespace/newlines from every string setting. Secrets
    # pasted into hosting dashboards (Render, HF, Railway) often carry a
    # trailing newline, which corrupts HTTP auth headers downstream.
    @field_validator("*", mode="before")
    @classmethod
    def _strip_whitespace(cls, v):
        return v.strip() if isinstance(v, str) else v

    # ── LLM provider ───────────────────────────────────────────────────────
    # Any OpenAI-compatible endpoint works: OpenRouter, Gemini, Groq, Ollama...
    # Swapping providers is a .env change, not a code change.
    llm_api_key: str = ""
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "meta-llama/llama-3.3-70b-instruct:free"

    # Per-step retry policy
    step_max_attempts: int = 3
    step_backoff_seconds: float = 2.0

    # ── Storage ────────────────────────────────────────────────────────────
    database_path: str = "auralis.db"

    # ── CRM ────────────────────────────────────────────────────────────────
    # "none" | "sheets" | "hubspot"  — pipeline skips the CRM step on "none"
    crm_provider: str = "none"

    # Google Sheets adapter
    sheets_credentials_path: str = "credentials.json"
    sheets_spreadsheet_name: str = "Auralis_Leads_CRM"
    sheets_worksheet_name: str = "Leads"

    # HubSpot adapter (stage 3)
    hubspot_access_token: str = ""

    # ── App ────────────────────────────────────────────────────────────────
    app_env: str = "development"
    allowed_origins: str = "*"  # comma-separated; tighten in production

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
