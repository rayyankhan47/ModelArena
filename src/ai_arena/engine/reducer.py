"""Round resolution logic for Grid Heist."""

from typing import Dict, Optional, Tuple

from pydantic import BaseModel, ValidationError

from .types import (
    Action,
    ActionType,
    BoardTile,
    CollectAction,
    Coord,
    Event,
    GameState,
    MoveAction,
    NegotiateAction,
    NoopAction,
    OpenVaultAction,
    ResolutionResult,
    ScanAction,
    SetTrapAction,
    StealAction,
    TileType,
)


TREASURE_VALUES = {
    TileType.TREASURE_1: 1,
    TileType.TREASURE_2: 2,
    TileType.TREASURE_3: 3,
}


def resolve_round(
    state: GameState,
    committed_actions: Dict[str, Action],
) -> ResolutionResult:
    """Resolve a single round of actions.

    Args:
        state: Current game state
        committed_actions: Dict of player_id -> Action (or action dict)

    Returns:
        ResolutionResult containing next state, events, and rewards
    """
    next_state = state.model_copy(deep=True)
    events = []
    rewards = {player_id: 0 for player_id in next_state.players.keys()}

    normalized_actions: Dict[str, Action] = {}

    # Pre-round: enforce trapped behavior and normalize actions
    for player_id, player in next_state.players.items():
        if player.trapped_for > 0:
            player.trapped_for = max(0, player.trapped_for - 1)
            normalized_actions[player_id] = NoopAction(reason="trapped")
            events.append(Event(
                round=state.round,
                kind="trapped_noop",
                payload={"player_id": player_id},
            ))
            continue

        action = _coerce_action(committed_actions.get(player_id))
        if action is None:
            action = NoopAction(reason="missing_action")

        if not _is_action_legal(next_state, player_id, action):
            normalized_actions[player_id] = NoopAction(reason="illegal_action")
            events.append(Event(
                round=state.round,
                kind="illegal_action",
                payload={"player_id": player_id, "action": _action_to_dict(action)},
            ))
        else:
            normalized_actions[player_id] = action

    # Resolve movement (simultaneous)
    current_positions = {
        pid: (p.pos.x, p.pos.y) for pid, p in next_state.players.items()
    }
    move_intents: Dict[str, Tuple[int, int]] = {}

    for player_id, action in normalized_actions.items():
        if isinstance(action, MoveAction):
            dest = _apply_direction(next_state.players[player_id].pos, action.dir)
            move_intents[player_id] = dest

    # Collision handling: any shared destination blocks all involved moves
    dest_counts: Dict[Tuple[int, int], int] = {}
    for dest in move_intents.values():
        dest_counts[dest] = dest_counts.get(dest, 0) + 1

    blocked_dests = {dest for dest, count in dest_counts.items() if count > 1}
    occupied_positions = set(current_positions.values())

    for player_id, dest in move_intents.items():
        if dest in blocked_dests:
            events.append(Event(
                round=state.round,
                kind="collision_blocked",
                payload={"player_id": player_id, "dest": dest},
            ))
            continue
        if dest in occupied_positions:
            events.append(Event(
                round=state.round,
                kind="move_blocked",
                payload={"player_id": player_id, "dest": dest, "reason": "occupied"},
            ))
            continue
        next_state.players[player_id].pos = Coord(x=dest[0], y=dest[1])

    # Resolve non-move actions deterministically by player_id
    for player_id in sorted(next_state.players.keys()):
        action = normalized_actions[player_id]
        player = next_state.players[player_id]
        pos = player.pos
        tile = next_state.board[pos.y][pos.x]

        if isinstance(action, MoveAction):
            continue

        if isinstance(action, CollectAction):
            if tile.type in TREASURE_VALUES:
                value = TREASURE_VALUES[tile.type]
                player.score += value
                rewards[player_id] += value
                next_state.board[pos.y][pos.x] = BoardTile(type=TileType.EMPTY)
                events.append(Event(
                    round=state.round,
                    kind="collect_treasure",
                    payload={"player_id": player_id, "value": value},
                ))
            elif tile.type == TileType.KEY:
                player.keys += 1
                next_state.board[pos.y][pos.x] = BoardTile(type=TileType.EMPTY)
                events.append(Event(
                    round=state.round,
                    kind="collect_key",
                    payload={"player_id": player_id},
                ))

        elif isinstance(action, OpenVaultAction):
            if tile.type == TileType.VAULT and player.keys > 0:
                player.keys -= 1
                player.score += 8
                rewards[player_id] += 8
                next_state.board[pos.y][pos.x] = BoardTile(type=TileType.EMPTY)
                events.append(Event(
                    round=state.round,
                    kind="open_vault",
                    payload={"player_id": player_id, "value": 8},
                ))

        elif isinstance(action, ScanAction):
            rewards[player_id] += 1
            events.append(Event(
                round=state.round,
                kind="scan_used",
                payload={"player_id": player_id},
            ))

        elif isinstance(action, SetTrapAction):
            dest = _apply_direction(player.pos, action.dir)
            if _is_valid_coord(dest, next_state.board):
                target_tile = next_state.board[dest[1]][dest[0]]
                if target_tile.type == TileType.EMPTY:
                    next_state.board[dest[1]][dest[0]] = BoardTile(type=TileType.TRAP)
                    events.append(Event(
                        round=state.round,
                        kind="trap_set",
                        payload={"player_id": player_id, "dest": dest},
                    ))

        elif isinstance(action, StealAction):
            target_id = action.target_player_id
            if target_id in next_state.players and _is_adjacent(player.pos, next_state.players[target_id].pos):
                target_player = next_state.players[target_id]
                if target_player.keys > 0:
                    target_player.keys -= 1
                    player.keys += 1
                    events.append(Event(
                        round=state.round,
                        kind="steal_key",
                        payload={"player_id": player_id, "target": target_id},
                    ))
                elif target_player.score > 0:
                    target_player.score -= 1
                    player.score += 1
                    rewards[player_id] += 1
                    rewards[target_id] -= 1
                    events.append(Event(
                        round=state.round,
                        kind="steal_point",
                        payload={"player_id": player_id, "target": target_id},
                    ))
                else:
                    events.append(Event(
                        round=state.round,
                        kind="steal_fail",
                        payload={"player_id": player_id, "target": target_id},
                    ))

        elif isinstance(action, NegotiateAction):
            events.append(Event(
                round=state.round,
                kind="negotiate_ignored",
                payload={"player_id": player_id},
            ))

    # Trigger traps after actions
    for player_id, player in next_state.players.items():
        tile = next_state.board[player.pos.y][player.pos.x]
        if tile.type == TileType.TRAP:
            player.trapped_for = max(player.trapped_for, 1)
            next_state.board[player.pos.y][player.pos.x] = BoardTile(type=TileType.EMPTY)
            events.append(Event(
                round=state.round,
                kind="trap_triggered",
                payload={"player_id": player_id},
            ))

    next_state.round = state.round + 1

    return ResolutionResult(next_state=next_state, events=events, rewards=rewards)


def _coerce_action(action_data: Optional[object]) -> Optional[Action]:
    """Convert action-like input into a validated Action."""
    if action_data is None:
        return None

    if isinstance(action_data, BaseModel):
        return action_data

    if isinstance(action_data, dict):
        action_type = action_data.get("type")
        try:
            if action_type == ActionType.MOVE.value:
                return MoveAction.model_validate(action_data)
            if action_type == ActionType.COLLECT.value:
                return CollectAction.model_validate(action_data)
            if action_type == ActionType.OPEN_VAULT.value:
                return OpenVaultAction.model_validate(action_data)
            if action_type == ActionType.SCAN.value:
                return ScanAction.model_validate(action_data)
            if action_type == ActionType.SET_TRAP.value:
                return SetTrapAction.model_validate(action_data)
            if action_type == ActionType.STEAL.value:
                return StealAction.model_validate(action_data)
            if action_type == ActionType.NEGOTIATE.value:
                return NegotiateAction.model_validate(action_data)
            if action_type == ActionType.NOOP.value:
                return NoopAction.model_validate(action_data)
        except ValidationError:
            return NoopAction(reason="invalid_action_schema")

    return NoopAction(reason="unknown_action_type")


def _is_action_legal(state: GameState, player_id: str, action: Action) -> bool:
    """Check whether an action is legal in the current state."""
    player = state.players[player_id]
    pos = player.pos
    tile = state.board[pos.y][pos.x]

    if isinstance(action, MoveAction):
        dest = _apply_direction(player.pos, action.dir)
        return _is_valid_coord(dest, state.board)

    if isinstance(action, CollectAction):
        return tile.type in TREASURE_VALUES or tile.type == TileType.KEY

    if isinstance(action, OpenVaultAction):
        return tile.type == TileType.VAULT and player.keys > 0

    if isinstance(action, ScanAction):
        return tile.type == TileType.SCANNER

    if isinstance(action, SetTrapAction):
        dest = _apply_direction(player.pos, action.dir)
        if not _is_valid_coord(dest, state.board):
            return False
        target_tile = state.board[dest[1]][dest[0]]
        return target_tile.type == TileType.EMPTY

    if isinstance(action, StealAction):
        target_id = action.target_player_id
        if target_id not in state.players:
            return False
        return _is_adjacent(player.pos, state.players[target_id].pos)

    if isinstance(action, NegotiateAction):
        return True

    if isinstance(action, NoopAction):
        return True

    return False


def _apply_direction(pos: Coord, direction: str) -> Tuple[int, int]:
    """Apply a direction to a coordinate and return destination tuple."""
    if direction == "N":
        return pos.x, pos.y - 1
    if direction == "E":
        return pos.x + 1, pos.y
    if direction == "S":
        return pos.x, pos.y + 1
    if direction == "W":
        return pos.x - 1, pos.y
    return pos.x, pos.y


def _is_valid_coord(coord: Tuple[int, int], board) -> bool:
    """Check if coordinate is within board bounds."""
    return 0 <= coord[0] < len(board[0]) and 0 <= coord[1] < len(board)


def _is_adjacent(a: Coord, b: Coord) -> bool:
    """Check if two coordinates are adjacent (cardinal directions only)."""
    return abs(a.x - b.x) + abs(a.y - b.y) == 1


def _action_to_dict(action: Action) -> Dict:
    """Convert action to plain dict for logging."""
    if hasattr(action, "model_dump"):
        return action.model_dump()
    return {"type": getattr(action, "type", "unknown")}
