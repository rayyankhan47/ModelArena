"""Unit tests for the Grid Heist engine."""

import unittest

from ai_arena.engine.generate import generate_initial_state
from ai_arena.engine.reducer import resolve_round
from ai_arena.engine.types import (
    BoardTile,
    Coord,
    GameState,
    MoveAction,
    NoopAction,
    OpenVaultAction,
    PlayerState,
    StealAction,
    TileType,
)


def _empty_board(size: int = 9):
    return [[BoardTile(type=TileType.EMPTY) for _ in range(size)] for _ in range(size)]


class TestEngine(unittest.TestCase):
    def test_generate_is_deterministic(self):
        state_a = generate_initial_state(seed="demo_seed", max_rounds=10)
        state_b = generate_initial_state(seed="demo_seed", max_rounds=10)

        tiles_a = [[tile.type for tile in row] for row in state_a.board]
        tiles_b = [[tile.type for tile in row] for row in state_b.board]

        self.assertEqual(tiles_a, tiles_b)

    def test_collision_blocks_movement(self):
        board = _empty_board()
        players = {
            "P1": PlayerState(player_id="P1", pos=Coord(x=0, y=0)),
            "P2": PlayerState(player_id="P2", pos=Coord(x=2, y=0)),
            "P3": PlayerState(player_id="P3", pos=Coord(x=0, y=8)),
            "P4": PlayerState(player_id="P4", pos=Coord(x=8, y=8)),
        }
        state = GameState(round=0, max_rounds=5, seed="test", board=board, players=players)

        actions = {
            "P1": MoveAction(dir="E"),
            "P2": MoveAction(dir="W"),
            "P3": NoopAction(),
            "P4": NoopAction(),
        }

        result = resolve_round(state, actions)
        self.assertEqual(result.next_state.players["P1"].pos, Coord(x=0, y=0))
        self.assertEqual(result.next_state.players["P2"].pos, Coord(x=2, y=0))

        collision_events = [e for e in result.events if e.kind == "collision_blocked"]
        self.assertTrue(len(collision_events) >= 1)

    def test_steal_transfers_key_first(self):
        board = _empty_board()
        players = {
            "P1": PlayerState(player_id="P1", pos=Coord(x=0, y=0)),
            "P2": PlayerState(player_id="P2", pos=Coord(x=1, y=0), keys=1),
            "P3": PlayerState(player_id="P3", pos=Coord(x=0, y=8)),
            "P4": PlayerState(player_id="P4", pos=Coord(x=8, y=8)),
        }
        state = GameState(round=0, max_rounds=5, seed="test", board=board, players=players)

        actions = {
            "P1": StealAction(target_player_id="P2"),
            "P2": NoopAction(),
            "P3": NoopAction(),
            "P4": NoopAction(),
        }

        result = resolve_round(state, actions)
        self.assertEqual(result.next_state.players["P1"].keys, 1)
        self.assertEqual(result.next_state.players["P2"].keys, 0)

    def test_open_vault_consumes_key_and_scores(self):
        board = _empty_board()
        board[0][0] = BoardTile(type=TileType.VAULT)

        players = {
            "P1": PlayerState(player_id="P1", pos=Coord(x=0, y=0), keys=1),
            "P2": PlayerState(player_id="P2", pos=Coord(x=1, y=0)),
            "P3": PlayerState(player_id="P3", pos=Coord(x=0, y=8)),
            "P4": PlayerState(player_id="P4", pos=Coord(x=8, y=8)),
        }
        state = GameState(round=0, max_rounds=5, seed="test", board=board, players=players)

        actions = {
            "P1": OpenVaultAction(),
            "P2": NoopAction(),
            "P3": NoopAction(),
            "P4": NoopAction(),
        }

        result = resolve_round(state, actions)
        self.assertEqual(result.next_state.players["P1"].keys, 0)
        self.assertEqual(result.next_state.players["P1"].score, 8)
        self.assertEqual(result.next_state.board[0][0].type, TileType.EMPTY)


if __name__ == "__main__":
    unittest.main()
