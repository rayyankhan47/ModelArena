"""Model routing for per-player models."""

from dataclasses import dataclass
from typing import Dict, Optional

from ai_arena.config import settings


@dataclass
class ModelRoute:
    provider: Optional[str]
    model: str


class ModelRouter:
    """Routes models per player."""

    def __init__(self):
        self.player_models: Dict[str, ModelRoute] = {
            "P1": ModelRoute(provider=settings.p1_provider or None, model=settings.p1_model),
            "P2": ModelRoute(provider=settings.p2_provider or None, model=settings.p2_model),
            "P3": ModelRoute(provider=settings.p3_provider or None, model=settings.p3_model),
            "P4": ModelRoute(provider=settings.p4_provider or None, model=settings.p4_model),
        }

    def get_player_model(self, player_id: str) -> ModelRoute:
        """Get the model route for a specific player."""
        return self.player_models[player_id]

    def planner_route(self) -> ModelRoute:
        """Model route for shared summarization / bookkeeping.

        Backward-compatible with earlier runner code. If legacy PLANNER_MODEL/PROVIDER
        is set, prefer it; otherwise fall back to P1's model.
        """
        model = settings.planner_model or self.player_models["P1"].model
        provider = settings.planner_provider or self.player_models["P1"].provider
        return ModelRoute(provider=provider or None, model=model)
