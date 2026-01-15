"""SQLite database schema for AI Arena logging and replay."""

import sqlite3
from typing import Dict, Any, List, Optional
import json
import time


# Database schema creation SQL
SCHEMA_SQL = """
-- Matches table: overall match metadata
CREATE TABLE IF NOT EXISTS matches (
    match_id TEXT PRIMARY KEY,
    seed TEXT NOT NULL,
    max_rounds INTEGER NOT NULL,
    created_at REAL NOT NULL,
    config_json TEXT NOT NULL
);

-- Rounds table: per-round state snapshots and results
CREATE TABLE IF NOT EXISTS rounds (
    match_id TEXT NOT NULL,
    round INTEGER NOT NULL,
    state_json TEXT NOT NULL,
    committed_actions_json TEXT NOT NULL,
    rewards_json TEXT NOT NULL,
    PRIMARY KEY (match_id, round),
    FOREIGN KEY (match_id) REFERENCES matches(match_id)
);

-- Events table: individual events from round resolution
CREATE TABLE IF NOT EXISTS events (
    match_id TEXT NOT NULL,
    round INTEGER NOT NULL,
    event_idx INTEGER NOT NULL,
    event_json TEXT NOT NULL,
    PRIMARY KEY (match_id, round, event_idx),
    FOREIGN KEY (match_id, round) REFERENCES rounds(match_id, round)
);

-- Agent calls table: Backboard API calls per agent per round
CREATE TABLE IF NOT EXISTS agent_calls (
    match_id TEXT NOT NULL,
    round INTEGER NOT NULL,
    player_id TEXT NOT NULL,
    phase TEXT NOT NULL,
    model TEXT NOT NULL,
    latency_ms INTEGER NOT NULL,
    request_json TEXT NOT NULL,
    response_json TEXT NOT NULL,
    PRIMARY KEY (match_id, round, player_id, phase),
    FOREIGN KEY (match_id, round) REFERENCES rounds(match_id, round)
);

-- Tool calls table: individual tool executions
CREATE TABLE IF NOT EXISTS tool_calls (
    match_id TEXT NOT NULL,
    round INTEGER NOT NULL,
    player_id TEXT NOT NULL,
    tool_idx INTEGER NOT NULL,
    tool_name TEXT NOT NULL,
    args_json TEXT NOT NULL,
    result_json TEXT NOT NULL,
    PRIMARY KEY (match_id, round, player_id, tool_idx),
    FOREIGN KEY (match_id, round) REFERENCES rounds(match_id, round)
);

-- Memory summaries table: agent memory states
CREATE TABLE IF NOT EXISTS memory_summaries (
    match_id TEXT NOT NULL,
    round INTEGER NOT NULL,
    player_id TEXT NOT NULL,
    private_summary TEXT NOT NULL,
    shared_summary TEXT NOT NULL,
    PRIMARY KEY (match_id, round, player_id),
    FOREIGN KEY (match_id, round) REFERENCES rounds(match_id, round)
);
"""


def create_tables(db_path: str) -> None:
    """Create all database tables if they don't exist."""
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


def serialize_game_state(state) -> str:
    """Convert GameState to JSON for storage."""
    return json.dumps({
        "round": state.round,
        "max_rounds": state.max_rounds,
        "seed": state.seed,
        "board": [[{"type": tile.type.value} for tile in row] for row in state.board],
        "players": {
            pid: {
                "player_id": p.player_id,
                "pos": {"x": p.pos.x, "y": p.pos.y},
                "score": p.score,
                "keys": p.keys,
                "trapped_for": p.trapped_for
            } for pid, p in state.players.items()
        },
        "active_deals": [deal.dict() for deal in state.active_deals]
    })


def serialize_actions(actions: Dict[str, Any]) -> str:
    """Convert action dict to JSON for storage."""
    return json.dumps(actions, default=lambda x: x.dict() if hasattr(x, 'dict') else str(x))


def serialize_rewards(rewards: Dict[str, int]) -> str:
    """Convert rewards dict to JSON for storage."""
    return json.dumps(rewards)


def serialize_event(event) -> str:
    """Convert Event to JSON for storage."""
    return json.dumps({
        "round": event.round,
        "kind": event.kind,
        "payload": event.payload
    })


def deserialize_game_state(json_str: str):
    """Convert stored JSON back to GameState-like dict."""
    return json.loads(json_str)


def deserialize_actions(json_str: str) -> Dict[str, Any]:
    """Convert stored JSON back to actions dict."""
    return json.loads(json_str)


def deserialize_rewards(json_str: str) -> Dict[str, int]:
    """Convert stored JSON back to rewards dict."""
    return json.loads(json_str)


def deserialize_event(json_str: str) -> Dict[str, Any]:
    """Convert stored JSON back to event dict."""
    return json.loads(json_str)