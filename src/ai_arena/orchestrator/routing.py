"""Model routing for planner/actor calls."""

from dataclasses import dataclass
from typing import Optional

from ai_arena.config import settings


@dataclass
class ModelRoute:
    provider: Optional[str]
    model: str


class ModelRouter:
    """Routes planner vs actor models per message."""

    def __init__(
        self,
        planner_model: str = settings.planner_model,
        actor_model: str = settings.actor_model,
        planner_provider: Optional[str] = settings.planner_provider or None,
        actor_provider: Optional[str] = settings.actor_provider or None,
    ):
        self.planner = ModelRoute(provider=planner_provider, model=planner_model)
        self.actor = ModelRoute(provider=actor_provider, model=actor_model)

    def planner_route(self) -> ModelRoute:
        return self.planner

    def actor_route(self) -> ModelRoute:
        return self.actor
