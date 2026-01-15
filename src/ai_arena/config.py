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

    # Backboard Model Routing
    planner_model: str = "gpt-4"
    actor_model: str = "gpt-3.5-turbo"
    planner_provider: str = ""
    actor_provider: str = ""

    # Search Rate Limiting
    search_budget_per_agent: int = 1
    search_cooldown_rounds: int = 3

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()