"""Prompt templates for AI Arena orchestration."""

from typing import Dict, List


RULES_SUMMARY = """You are playing Grid Heist on a 9x9 board.
Goal: maximize score over N rounds.
Tiles:
- treasure_1/2/3: collect for +1/+2/+3 points
- key: collect to gain a key
- vault: open with a key to gain +8 points (consumes 1 key)
- scanner: optional scan action (small reward)
- trap: placed by players; stepping on it causes trapped_for=1 next round
Actions (one per round):
MOVE (N/E/S/W), COLLECT, OPEN_VAULT, SCAN, SET_TRAP (adjacent empty), STEAL (adjacent), NOOP
Collisions: if two players move to same destination, all those moves fail.
Steal: steals 1 key if target has one, else steals 1 point (target floored at 0).
"""


ACTION_SCHEMA = """Return ONLY a strict JSON object for the action:
{ "type": "move", "dir": "N|E|S|W" }
{ "type": "collect" }
{ "type": "open_vault" }
{ "type": "scan" }
{ "type": "set_trap", "dir": "N|E|S|W" }
{ "type": "steal", "target_player_id": "P2" }
{ "type": "noop", "reason": "..." }
"""


def system_prompt(player_id: str) -> str:
    return (
        "You are a competitive agent in Grid Heist. "
        f"Your player_id is {player_id}. "
        "Always follow the rules and respect action schema constraints. "
        "If you are asked for an action, return ONLY JSON."
    )


def planning_prompt(state_summary: str, shared_summary: str) -> str:
    return (
        "Plan your next move for the upcoming round. "
        "Provide a brief plan and any opponent observations.\n\n"
        f"Shared summary:\n{shared_summary}\n\n"
        f"State:\n{state_summary}\n\n"
        "Respond in 3-6 bullet points.\n"
        "Include a final line: Citations: [R#], [S#] or Citations: none."
    )


def negotiation_prompt(state_summary: str, shared_summary: str) -> str:
    return (
        "You may send ONE short public negotiation message (<= 2 sentences). "
        "You can propose or accept/reject deals verbally. "
        "Be concise.\n\n"
        f"Shared summary:\n{shared_summary}\n\n"
        f"State:\n{state_summary}\n\n"
        "Respond with the message only."
    )


def action_prompt(state_summary: str, shared_summary: str) -> str:
    return (
        "Choose your action for this round. "
        "Return ONLY strict JSON matching one of the allowed schemas.\n\n"
        f"Shared summary:\n{shared_summary}\n\n"
        f"State:\n{state_summary}\n\n"
        f"{ACTION_SCHEMA}"
    )
