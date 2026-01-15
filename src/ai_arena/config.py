"""Configuration management for AI Arena."""

try:
    from pydantic_settings import BaseSettings  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    from pydantic import BaseSettings


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

    # Legacy routing (optional fallback)
    planner_model: str = ""
    planner_provider: str = ""
    actor_model: str = ""
    actor_provider: str = ""

    # Search Rate Limiting
    enable_web_search: bool = False
    search_budget_per_agent: int = 1
    search_cooldown_rounds: int = 3

    # Cost Guardrails
    max_llm_calls_per_match: int = 250

    class Config:
        env_file = ".env"
        case_sensitive = False

    def model_post_init(self, __context):  # type: ignore[override]
        """Fallback to legacy planner/actor env vars if per-player not set."""
        has_per_player = any([
            self.p1_model, self.p2_model, self.p3_model, self.p4_model
        ])
        if not has_per_player and (self.planner_model or self.actor_model):
            self.p1_model = self.planner_model or self.p1_model
            self.p1_provider = self.planner_provider or self.p1_provider
            actor_model = self.actor_model or self.p4_model
            actor_provider = self.actor_provider or self.p4_provider
            self.p2_model = actor_model
            self.p2_provider = actor_provider
            self.p3_model = actor_model
            self.p3_provider = actor_provider
            self.p4_model = actor_model
            self.p4_provider = actor_provider


# Global settings instance
settings = Settings()