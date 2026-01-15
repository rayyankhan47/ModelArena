"""Database connection and core operations for AI Arena logging."""

import sqlite3
import json
import uuid
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

from .schema import (
    create_tables,
    serialize_game_state,
    serialize_actions,
    serialize_rewards,
    serialize_event,
    deserialize_game_state,
    deserialize_actions,
    deserialize_rewards,
    deserialize_event
)


class Database:
    """SQLite database wrapper for AI Arena logging and replay."""

    def __init__(self, db_path: str = "ai_arena.db"):
        """Initialize database connection and create tables."""
        self.db_path = Path(db_path)
        create_tables(str(self.db_path))

    def _get_conn(self) -> sqlite3.Connection:
        """Get a database connection."""
        return sqlite3.connect(str(self.db_path))

    def create_match(self, seed: str, max_rounds: int, config: Dict[str, Any]) -> str:
        """Create a new match record and return its ID."""
        match_id = str(uuid.uuid4())
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO matches (match_id, seed, max_rounds, created_at, config_json)
                VALUES (?, ?, ?, ?, ?)
            """, (
                match_id,
                seed,
                max_rounds,
                time.time(),
                json.dumps(config)
            ))
            conn.commit()

        return match_id

    def log_round(
        self,
        match_id: str,
        round_num: int,
        state,
        committed_actions: Dict[str, Any],
        rewards: Dict[str, int]
    ) -> None:
        """Log a complete round with state, actions, and rewards."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO rounds (match_id, round, state_json, committed_actions_json, rewards_json)
                VALUES (?, ?, ?, ?, ?)
            """, (
                match_id,
                round_num,
                serialize_game_state(state),
                serialize_actions(committed_actions),
                serialize_rewards(rewards)
            ))
            conn.commit()

    def log_events(self, match_id: str, round_num: int, events: List) -> None:
        """Log events from round resolution."""
        with self._get_conn() as conn:
            for idx, event in enumerate(events):
                conn.execute("""
                    INSERT INTO events (match_id, round, event_idx, event_json)
                    VALUES (?, ?, ?, ?)
                """, (
                    match_id,
                    round_num,
                    idx,
                    serialize_event(event)
                ))
            conn.commit()

    def log_agent_call(
        self,
        match_id: str,
        round_num: int,
        player_id: str,
        phase: str,
        model: str,
        latency_ms: int,
        request: Dict[str, Any],
        response: Dict[str, Any]
    ) -> None:
        """Log a Backboard API call."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO agent_calls (match_id, round, player_id, phase, model, latency_ms, request_json, response_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                match_id,
                round_num,
                player_id,
                phase,
                model,
                latency_ms,
                json.dumps(request),
                json.dumps(response)
            ))
            conn.commit()

    def log_tool_calls(self, match_id: str, round_num: int, player_id: str, tool_calls: List[Dict[str, Any]]) -> None:
        """Log tool calls for an agent in a round."""
        with self._get_conn() as conn:
            for idx, tool_call in enumerate(tool_calls):
                conn.execute("""
                    INSERT INTO tool_calls (match_id, round, player_id, tool_idx, tool_name, args_json, result_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    match_id,
                    round_num,
                    player_id,
                    idx,
                    tool_call.get("name", ""),
                    json.dumps(tool_call.get("args", {})),
                    json.dumps(tool_call.get("result", {}))
                ))
            conn.commit()

    def log_memory_summaries(
        self,
        match_id: str,
        round_num: int,
        player_id: str,
        private_summary: str,
        shared_summary: str
    ) -> None:
        """Log memory summaries for an agent."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO memory_summaries (match_id, round, player_id, private_summary, shared_summary)
                VALUES (?, ?, ?, ?, ?)
            """, (
                match_id,
                round_num,
                player_id,
                private_summary,
                shared_summary
            ))
            conn.commit()

    def get_match_info(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get basic match information."""
        with self._get_conn() as conn:
            row = conn.execute("""
                SELECT seed, max_rounds, created_at, config_json
                FROM matches
                WHERE match_id = ?
            """, (match_id,)).fetchone()

            if row:
                return {
                    "match_id": match_id,
                    "seed": row[0],
                    "max_rounds": row[1],
                    "created_at": row[2],
                    "config": json.loads(row[3])
                }
        return None

    def get_rounds(self, match_id: str) -> List[Dict[str, Any]]:
        """Get all rounds for a match."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT round, state_json, committed_actions_json, rewards_json
                FROM rounds
                WHERE match_id = ?
                ORDER BY round
            """, (match_id,)).fetchall()

            return [{
                "round": row[0],
                "state": deserialize_game_state(row[1]),
                "actions": deserialize_actions(row[2]),
                "rewards": deserialize_rewards(row[3])
            } for row in rows]

    def get_events(self, match_id: str, round_num: int) -> List[Dict[str, Any]]:
        """Get events for a specific round."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT event_json
                FROM events
                WHERE match_id = ? AND round = ?
                ORDER BY event_idx
            """, (match_id, round_num)).fetchall()

            return [deserialize_event(row[0]) for row in rows]

    def get_agent_calls(self, match_id: str, round_num: int, player_id: str) -> List[Dict[str, Any]]:
        """Get agent calls for a specific round and player."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT phase, model, latency_ms, request_json, response_json
                FROM agent_calls
                WHERE match_id = ? AND round = ? AND player_id = ?
                ORDER BY phase
            """, (match_id, round_num, player_id)).fetchall()

            return [{
                "phase": row[0],
                "model": row[1],
                "latency_ms": row[2],
                "request": json.loads(row[3]),
                "response": json.loads(row[4])
            } for row in rows]

    def list_matches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent matches."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT match_id, seed, max_rounds, created_at
                FROM matches
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,)).fetchall()

            return [{
                "match_id": row[0],
                "seed": row[1],
                "max_rounds": row[2],
                "created_at": row[3]
            } for row in rows]