"""Legal action computation for Grid Heist."""

from typing import Dict, List, Set

from .types import (
    ActionType, Coord, GameState, LegalActionSummary, PlayerState,
    TileType
)


def legal_actions(state: GameState, player_id: str) -> List[LegalActionSummary]:
    """Compute all legal actions for a player in the current state.

    Args:
        state: Current game state
        player_id: Player to check actions for

    Returns:
        List of legal action summaries with descriptions
    """
    if player_id not in state.players:
        return [LegalActionSummary(
            type=ActionType.NOOP.value,
            description="Invalid player ID",
            valid=False,
            reason="Player does not exist"
        )]

    player = state.players[player_id]

    # If trapped, only NOOP is allowed
    if player.trapped_for > 0:
        return [LegalActionSummary(
            type=ActionType.NOOP.value,
            description="Do nothing (trapped)",
            valid=True
        )]

    actions = []

    # MOVE actions - adjacent tiles
    move_dirs = _get_adjacent_directions(player.pos)
    for direction, coord in move_dirs.items():
        if _is_valid_coord(coord, state.board):
            actions.append(LegalActionSummary(
                type=ActionType.MOVE.value,
                description=f"Move {direction} to ({coord[0]}, {coord[1]})",
                valid=True
            ))

    # COLLECT - if on treasure or key
    current_tile = _get_tile_at(state.board, (player.pos.x, player.pos.y))
    if current_tile.type in [TileType.TREASURE_1, TileType.TREASURE_2, TileType.TREASURE_3, TileType.KEY]:
        tile_name = current_tile.type.value.replace('_', ' ')
        actions.append(LegalActionSummary(
            type=ActionType.COLLECT.value,
            description=f"Collect {tile_name}",
            valid=True
        ))

    # OPEN_VAULT - if on vault and has key
    if current_tile.type == TileType.VAULT and player.keys > 0:
        actions.append(LegalActionSummary(
            type=ActionType.OPEN_VAULT.value,
            description="Open vault (+8 points, consumes 1 key)",
            valid=True
        ))

    # SCAN - if on scanner
    if current_tile.type == TileType.SCANNER:
        actions.append(LegalActionSummary(
            type=ActionType.SCAN.value,
            description="Use scanner",
            valid=True
        ))

    # SET_TRAP - on adjacent empty tiles
    for direction, coord in move_dirs.items():
        if _is_valid_coord(coord, state.board):
            adjacent_tile = _get_tile_at(state.board, coord)
            if adjacent_tile.type == TileType.EMPTY:
                actions.append(LegalActionSummary(
                    type=ActionType.SET_TRAP.value,
                    description=f"Set trap {direction} at ({coord[0]}, {coord[1]})",
                    valid=True
                ))

    # STEAL - from adjacent players
    adjacent_players = _get_adjacent_players(state, player_id)
    for adj_player_id in adjacent_players:
        actions.append(LegalActionSummary(
            type=ActionType.STEAL.value,
            description=f"Steal from {adj_player_id}",
            valid=True
        ))

    # NEGOTIATE - always available
    actions.append(LegalActionSummary(
        type=ActionType.NEGOTIATE.value,
        description="Send negotiation message",
        valid=True
    ))

    # NOOP - always available as fallback
    actions.append(LegalActionSummary(
        type=ActionType.NOOP.value,
        description="Do nothing",
        valid=True
    ))

    return actions


def _get_adjacent_directions(pos: Coord) -> Dict[str, tuple]:
    """Get adjacent coordinates in cardinal directions as (x, y) tuples."""
    return {
        "N": (pos.x, pos.y - 1),
        "E": (pos.x + 1, pos.y),
        "S": (pos.x, pos.y + 1),
        "W": (pos.x - 1, pos.y),
    }


def _is_valid_coord(coord: tuple, board: List[List]) -> bool:
    """Check if coordinate is within board bounds."""
    return 0 <= coord[0] < len(board[0]) and 0 <= coord[1] < len(board)


def _get_tile_at(board: List[List], coord: tuple):
    """Get tile at coordinate."""
    return board[coord[1]][coord[0]]


def _get_adjacent_players(state: GameState, player_id: str) -> Set[str]:
    """Get IDs of players adjacent to the given player."""
    player = state.players[player_id]
    adjacent_coords = set(_get_adjacent_directions(player.pos).values())

    adjacent_players = set()
    for other_id, other_player in state.players.items():
        if other_id == player_id:
            continue
        if (other_player.pos.x, other_player.pos.y) in adjacent_coords:
            adjacent_players.add(other_id)

    return adjacent_players