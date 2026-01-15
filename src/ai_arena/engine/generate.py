"""Board generation and initial state creation for Grid Heist."""

import random
from typing import Dict, List

from .types import BoardTile, Coord, GameState, PlayerState, TileType


def generate_initial_state(
    seed: str,
    max_rounds: int = 15,
    board_size: int = 9
) -> GameState:
    """Generate initial game state with seeded board and player spawns.

    Args:
        seed: String seed for deterministic generation
        max_rounds: Maximum rounds for the match
        board_size: Size of the square board (default 9)

    Returns:
        Initial GameState ready for play
    """
    # Set random seed for deterministic generation
    random.seed(seed)

    # Generate board
    board = _generate_board(board_size)

    # Create players at corners
    players = _generate_players()

    return GameState(
        round=0,
        max_rounds=max_rounds,
        seed=seed,
        board=board,
        players=players,
        active_deals=[]
    )


def _generate_board(size: int) -> List[List[BoardTile]]:
    """Generate a deterministic board layout.

    Places tiles in a balanced but random distribution.
    """
    # Define tile counts for balance
    tile_counts = {
        TileType.TREASURE_1: 8,
        TileType.TREASURE_2: 6,
        TileType.TREASURE_3: 4,
        TileType.KEY: 6,
        TileType.VAULT: 4,
        TileType.SCANNER: 4,
    }

    # Calculate total special tiles needed
    total_special = sum(tile_counts.values())

    # Create list of all tiles to place
    tiles_to_place = []
    for tile_type, count in tile_counts.items():
        tiles_to_place.extend([tile_type] * count)

    # Fill remaining with empty tiles
    empty_count = size * size - total_special
    tiles_to_place.extend([TileType.EMPTY] * empty_count)

    # Shuffle for random placement
    random.shuffle(tiles_to_place)

    # Create board grid
    board = []
    idx = 0
    for y in range(size):
        row = []
        for x in range(size):
            tile_type = tiles_to_place[idx]
            row.append(BoardTile(type=tile_type))
            idx += 1
        board.append(row)

    return board


def _generate_players() -> Dict[str, PlayerState]:
    """Generate 4 players at corner positions."""
    corners = [
        Coord(x=0, y=0),      # Top-left
        Coord(x=8, y=0),      # Top-right
        Coord(x=0, y=8),      # Bottom-left
        Coord(x=8, y=8),      # Bottom-right
    ]

    players = {}
    for i, pos in enumerate(corners, 1):
        player_id = f"P{i}"
        players[player_id] = PlayerState(
            player_id=player_id,
            pos=pos,
            score=0,
            keys=0,
            trapped_for=0
        )

    return players