"""Tool definitions and execution for Backboard tool calls."""

import json
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ai_arena.engine.rules import legal_actions
from ai_arena.engine.types import GameState


def tool_definitions() -> List[Dict[str, Any]]:
    """Return Backboard-compatible tool definitions."""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_public_state",
                "description": "Get public game state summary.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_player_state",
                "description": "Get a specific player's private state.",
                "parameters": {
                    "type": "object",
                    "properties": {"player_id": {"type": "string"}},
                    "required": ["player_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_legal_actions",
                "description": "List legal actions for a player.",
                "parameters": {
                    "type": "object",
                    "properties": {"player_id": {"type": "string"}},
                    "required": ["player_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "propose_deal",
                "description": "Propose a deal to another player.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to_player_id": {"type": "string"},
                        "terms": {"type": "string"},
                    },
                    "required": ["to_player_id", "terms"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "accept_deal",
                "description": "Accept a deal by deal_id.",
                "parameters": {
                    "type": "object",
                    "properties": {"deal_id": {"type": "string"}},
                    "required": ["deal_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "reject_deal",
                "description": "Reject a deal by deal_id.",
                "parameters": {
                    "type": "object",
                    "properties": {"deal_id": {"type": "string"}},
                    "required": ["deal_id"],
                },
            },
        },
    ]


@dataclass
class ToolContext:
    state: GameState
    player_id: str
    deals: List[Dict[str, Any]]


class ToolExecutor:
    """Execute tool calls requested by Backboard."""

    def execute(self, tool_name: str, args: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        if tool_name == "get_public_state":
            return _public_state(context.state)
        if tool_name == "get_player_state":
            return _player_state(context.state, args.get("player_id"))
        if tool_name == "list_legal_actions":
            return _legal_actions(context.state, args.get("player_id"))
        if tool_name == "propose_deal":
            return _propose_deal(context, args.get("to_player_id"), args.get("terms"))
        if tool_name == "accept_deal":
            return _update_deal(context, args.get("deal_id"), "accepted")
        if tool_name == "reject_deal":
            return _update_deal(context, args.get("deal_id"), "rejected")
        return {"error": f"Unknown tool: {tool_name}"}


def _public_state(state: GameState) -> Dict[str, Any]:
    return {
        "round": state.round,
        "max_rounds": state.max_rounds,
        "players": {
            pid: {
                "pos": {"x": p.pos.x, "y": p.pos.y},
                "score": p.score,
                "keys": p.keys,
                "trapped_for": p.trapped_for,
            }
            for pid, p in state.players.items()
        },
    }


def _player_state(state: GameState, player_id: Optional[str]) -> Dict[str, Any]:
    if not player_id or player_id not in state.players:
        return {"error": "player_id not found"}
    p = state.players[player_id]
    return {
        "player_id": p.player_id,
        "pos": {"x": p.pos.x, "y": p.pos.y},
        "score": p.score,
        "keys": p.keys,
        "trapped_for": p.trapped_for,
    }


def _legal_actions(state: GameState, player_id: Optional[str]) -> Dict[str, Any]:
    if not player_id or player_id not in state.players:
        return {"error": "player_id not found"}
    actions = legal_actions(state, player_id)
    return {"actions": [a.model_dump() for a in actions]}


def _propose_deal(context: ToolContext, to_player_id: Optional[str], terms: Optional[str]) -> Dict[str, Any]:
    if not to_player_id or not terms:
        return {"error": "to_player_id and terms required"}
    deal_id = str(uuid.uuid4())
    deal = {
        "deal_id": deal_id,
        "from_player": context.player_id,
        "to_player": to_player_id,
        "terms": terms,
        "status": "proposed",
    }
    context.deals.append(deal)
    return {"deal_id": deal_id, "status": "proposed"}


def _update_deal(context: ToolContext, deal_id: Optional[str], status: str) -> Dict[str, Any]:
    if not deal_id:
        return {"error": "deal_id required"}
    for deal in context.deals:
        if deal["deal_id"] == deal_id:
            deal["status"] = status
            return {"deal_id": deal_id, "status": status}
    return {"error": "deal not found"}


def parse_tool_calls(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract tool calls from a Backboard response in a robust way."""
    calls = response.get("tool_calls") or []
    parsed = []
    for call in calls:
        tool_call_id = call.get("id") or call.get("tool_call_id") or ""
        function_info = call.get("function") or {}
        name = function_info.get("name") or call.get("name") or ""
        args = function_info.get("arguments") or call.get("arguments") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {"_raw": args}
        parsed.append({
            "tool_call_id": tool_call_id,
            "name": name,
            "args": args if isinstance(args, dict) else {},
        })
    return parsed
