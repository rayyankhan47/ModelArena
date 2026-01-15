"""High-level logging interface for AI Arena matches."""

import time
from typing import Dict, Any, List, Optional

from .db import Database


class MatchLogger:
    """Handles logging for a single match."""

    def __init__(self, db_path: str = "ai_arena.db"):
        """Initialize logger with database path."""
        self.db = Database(db_path)
        self.match_id: Optional[str] = None

    def start_match(self, seed: str, max_rounds: int, config: Dict[str, Any]) -> str:
        """Start a new match and return the match ID."""
        self.match_id = self.db.create_match(seed, max_rounds, config)
        return self.match_id

    def log_round_complete(self, round_num: int, state, actions: Dict[str, Any], rewards: Dict[str, int]) -> None:
        """Log a complete round."""
        if not self.match_id:
            raise ValueError("Match not started")
        self.db.log_round(self.match_id, round_num, state, actions, rewards)

    def log_events(self, round_num: int, events: List) -> None:
        """Log events from round resolution."""
        if not self.match_id:
            raise ValueError("Match not started")
        self.db.log_events(self.match_id, round_num, events)

    def log_agent_call(
        self,
        round_num: int,
        player_id: str,
        phase: str,
        model: str,
        latency_ms: int,
        request: Dict[str, Any],
        response: Dict[str, Any]
    ) -> None:
        """Log a Backboard API call."""
        if not self.match_id:
            raise ValueError("Match not started")
        self.db.log_agent_call(self.match_id, round_num, player_id, phase, model, latency_ms, request, response)

    def log_tool_calls(self, round_num: int, player_id: str, tool_calls: List[Dict[str, Any]]) -> None:
        """Log tool calls for an agent."""
        if not self.match_id:
            raise ValueError("Match not started")
        self.db.log_tool_calls(self.match_id, round_num, player_id, tool_calls)

    def log_memory_summaries(
        self,
        round_num: int,
        player_id: str,
        private_summary: str,
        shared_summary: str
    ) -> None:
        """Log memory summaries for an agent."""
        if not self.match_id:
            raise ValueError("Match not started")
        self.db.log_memory_summaries(self.match_id, round_num, player_id, private_summary, shared_summary)


class MatchReplay:
    """Handles replaying a match from database."""

    def __init__(self, db_path: str = "ai_arena.db"):
        """Initialize replay with database path."""
        self.db = Database(db_path)

    def get_match_info(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get basic match information."""
        return self.db.get_match_info(match_id)

    def get_round_count(self, match_id: str) -> int:
        """Get the number of rounds in a match."""
        rounds = self.db.get_rounds(match_id)
        return len(rounds)

    def get_round_data(self, match_id: str, round_num: int) -> Optional[Dict[str, Any]]:
        """Get data for a specific round."""
        rounds = self.db.get_rounds(match_id)
        for round_data in rounds:
            if round_data["round"] == round_num:
                # Add events for this round
                round_data["events"] = self.db.get_events(match_id, round_num)
                return round_data
        return None

    def get_agent_calls_for_round(self, match_id: str, round_num: int, player_id: str) -> List[Dict[str, Any]]:
        """Get agent calls for a specific round and player."""
        return self.db.get_agent_calls(match_id, round_num, player_id)

    def get_tool_calls_for_round(self, match_id: str, round_num: int) -> List[Dict[str, Any]]:
        """Get tool calls for a specific round across all players."""
        return self.db.get_tool_calls(match_id, round_num)

    def list_recent_matches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent matches."""
        return self.db.list_matches(limit)