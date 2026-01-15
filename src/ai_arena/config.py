"""Configuration management for AI Arena."""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Backboard API
    backboard_api_key: str = ""
    backboard_base_url: str = "https://app.backboard.io/api"
    backboard_timeout: int = 30

    # Match Configuration
    default_match_rounds: int = 15
    default_match_seed: str = "demo_1"

    # UI Configuration
    ui_fullscreen: bool = True
    ui_default_speed: float = 1.0

    # Backboard Model Routing (per-player models)
    p1_model: str = "gpt-4"
    p1_provider: str = "openai"
    p2_model: str = "claude-3-5-sonnet"
    p2_provider: str = "anthropic"
    p3_model: str = "gemini-1.5-pro"
    p3_provider: str = "google"
    p4_model: str = "gpt-3.5-turbo"
    p4_provider: str = "openai"

    # Search Rate Limiting
    enable_web_search: bool = False
    search_budget_per_agent: int = 1
    search_cooldown_rounds: int = 3

    # Cost Guardrails
    max_llm_calls_per_match: int = 250

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()