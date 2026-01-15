"""Core data types for the Grid Heist game engine."""

from enum import Enum
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field


class Coord(BaseModel):
    """A coordinate on the 9x9 grid."""
    x: int = Field(ge=0, le=8)
    y: int = Field(ge=0, le=8)


class TileType(str, Enum):
    """Types of tiles on the board."""
    EMPTY = "empty"
    TREASURE_1 = "treasure_1"
    TREASURE_2 = "treasure_2"
    TREASURE_3 = "treasure_3"
    KEY = "key"
    VAULT = "vault"
    SCANNER = "scanner"
    TRAP = "trap"


class Phase(str, Enum):
    """Game phases in a round."""
    SNAPSHOT = "snapshot"
    PLAN = "plan"
    NEGOTIATE = "negotiate"
    COMMIT = "commit"
    RESOLVE = "resolve"
    MEMORY_WRITEBACK = "memory_writeback"


class ActionType(str, Enum):
    """Types of actions players can take."""
    MOVE = "move"
    COLLECT = "collect"
    OPEN_VAULT = "open_vault"
    SCAN = "scan"
    SET_TRAP = "set_trap"
    STEAL = "steal"
    NEGOTIATE = "negotiate"
    NOOP = "noop"


class MoveAction(BaseModel):
    """Move to an adjacent tile."""
    type: str = ActionType.MOVE.value
    dir: str = Field(pattern="^(N|E|S|W)$")


class CollectAction(BaseModel):
    """Collect treasure or key on current tile."""
    type: str = ActionType.COLLECT.value


class OpenVaultAction(BaseModel):
    """Open vault on current tile if player has key."""
    type: str = ActionType.OPEN_VAULT.value


class ScanAction(BaseModel):
    """Use scanner on current tile."""
    type: str = ActionType.SCAN.value


class SetTrapAction(BaseModel):
    """Place trap on adjacent tile."""
    type: str = ActionType.SET_TRAP.value
    dir: str = Field(pattern="^(N|E|S|W)$")


class StealAction(BaseModel):
    """Steal from adjacent player."""
    type: str = ActionType.STEAL.value
    target_player_id: str


class NegotiateAction(BaseModel):
    """Send negotiation message or deal proposal."""
    type: str = ActionType.NEGOTIATE.value
    message: Optional[str] = None
    propose_deal_to: Optional[str] = None
    terms: Optional[str] = None
    accept_deal_id: Optional[str] = None
    reject_deal_id: Optional[str] = None


class NoopAction(BaseModel):
    """Do nothing (fallback or when trapped)."""
    type: str = ActionType.NOOP.value
    reason: Optional[str] = None


# Union type for all possible actions
Action = Union[
    MoveAction,
    CollectAction,
    OpenVaultAction,
    ScanAction,
    SetTrapAction,
    StealAction,
    NegotiateAction,
    NoopAction,
]


class PlayerState(BaseModel):
    """State of a single player."""
    player_id: str
    pos: Coord
    score: int = 0
    keys: int = 0
    trapped_for: int = 0  # rounds remaining unable to act


class BoardTile(BaseModel):
    """A tile on the board."""
    type: TileType


class Deal(BaseModel):
    """A negotiation deal between players."""
    deal_id: str
    from_player: str
    to_player: str
    terms: str
    created_round: int
    status: str = "proposed"  # proposed, accepted, rejected, expired


class GameState(BaseModel):
    """Complete game state."""
    round: int = 0
    max_rounds: int = 15
    seed: str
    board: List[List[BoardTile]]  # 9x9 grid
    players: Dict[str, PlayerState]
    active_deals: List[Deal] = Field(default_factory=list)


class Event(BaseModel):
    """An event that occurred during resolution."""
    round: int
    kind: str  # e.g., "move_success", "steal_fail", "collision_blocked"
    payload: Dict = Field(default_factory=dict)


class ResolutionResult(BaseModel):
    """Result of resolving a round."""
    next_state: GameState
    events: List[Event] = Field(default_factory=list)
    rewards: Dict[str, int] = Field(default_factory=dict)  # player_id -> reward delta


class LegalActionSummary(BaseModel):
    """Summary of a legal action for tool usage."""
    type: str
    description: str
    valid: bool = True
    reason: Optional[str] = None