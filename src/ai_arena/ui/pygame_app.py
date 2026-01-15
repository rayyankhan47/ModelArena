"""Pygame visualization for AI Arena (Grid Heist)."""

import sys
import time
import random
from typing import Dict, List, Tuple

import pygame

from ai_arena.engine.generate import generate_initial_state
from ai_arena.engine.reducer import resolve_round
from ai_arena.engine.rules import legal_actions
from ai_arena.engine.types import (
    ActionType,
    CollectAction,
    GameState,
    MoveAction,
    NoopAction,
    OpenVaultAction,
    ScanAction,
    SetTrapAction,
    StealAction,
    TileType,
)


BOARD_SIZE = 9
WINDOW_BG = (18, 18, 22)
GRID_COLOR = (40, 40, 48)
TEXT_COLOR = (230, 230, 240)
TILE_COLORS = {
    TileType.EMPTY: (30, 30, 36),
    TileType.TREASURE_1: (64, 160, 96),
    TileType.TREASURE_2: (50, 140, 200),
    TileType.TREASURE_3: (200, 160, 80),
    TileType.KEY: (210, 190, 60),
    TileType.VAULT: (120, 80, 160),
    TileType.SCANNER: (80, 140, 160),
    TileType.TRAP: (140, 60, 60),
}
PLAYER_COLORS = {
    "P1": (220, 90, 90),
    "P2": (90, 160, 220),
    "P3": (90, 200, 140),
    "P4": (200, 180, 80),
}


def run_demo(seed: str = "demo_1", rounds: int = 15, speed: float = 1.0, fullscreen: bool = True):
    """Run a live demo with simple random agents."""
    pygame.init()

    if fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((1200, 800))

    pygame.display.set_caption("AI Arena - Grid Heist")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 18)
    small_font = pygame.font.SysFont("Arial", 14)

    state = generate_initial_state(seed=seed, max_rounds=rounds)
    event_log: List[str] = []
    paused = False
    step_round = False
    last_tick = time.time()
    seconds_per_round = max(0.2, 1.0 / speed)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit(0)
                if event.key == pygame.K_SPACE:
                    paused = not paused
                if event.key == pygame.K_RIGHT:
                    step_round = True
                if event.key == pygame.K_MINUS:
                    seconds_per_round = min(5.0, seconds_per_round + 0.2)
                if event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    seconds_per_round = max(0.1, seconds_per_round - 0.2)

        now = time.time()
        if state.round >= state.max_rounds:
            paused = True

        if (not paused or step_round) and (now - last_tick) >= seconds_per_round:
            actions = _select_random_actions(state)
            result = resolve_round(state, actions)
            state = result.next_state
            for ev in result.events[-6:]:
                event_log.append(f"R{ev.round}: {ev.kind} {ev.payload}")
            event_log = event_log[-6:]
            last_tick = now
            step_round = False

        _render_frame(screen, state, event_log, font, small_font, paused, seconds_per_round)
        pygame.display.flip()
        clock.tick(60)


def _select_random_actions(state: GameState) -> Dict[str, object]:
    """Select simple random actions for demo agents."""
    actions: Dict[str, object] = {}
    for player_id, player in state.players.items():
        if player.trapped_for > 0:
            actions[player_id] = NoopAction(reason="trapped")
            continue

        tile = state.board[player.pos.y][player.pos.x]
        if tile.type in [TileType.TREASURE_1, TileType.TREASURE_2, TileType.TREASURE_3, TileType.KEY]:
            actions[player_id] = CollectAction()
            continue
        if tile.type == TileType.VAULT and player.keys > 0:
            actions[player_id] = OpenVaultAction()
            continue
        if tile.type == TileType.SCANNER:
            if random.random() < 0.4:
                actions[player_id] = ScanAction()
                continue

        # Prefer movement over other actions for a lively demo
        move_dirs = ["N", "E", "S", "W"]
        random.shuffle(move_dirs)
        moved = False
        for direction in move_dirs:
            action = MoveAction(dir=direction)
            if _is_action_legal(state, player_id, action):
                actions[player_id] = action
                moved = True
                break
        if not moved:
            actions[player_id] = NoopAction()
    return actions


def _is_action_legal(state: GameState, player_id: str, action: object) -> bool:
    """Lightweight legality check using existing rule summaries."""
    summaries = legal_actions(state, player_id)
    action_type = getattr(action, "type", None)
    return any(s.type == action_type for s in summaries)


def _render_frame(screen, state: GameState, event_log: List[str], font, small_font, paused: bool, seconds_per_round: float):
    screen.fill(WINDOW_BG)
    width, height = screen.get_size()

    # Layout regions
    board_size_px = min(int(width * 0.6), int(height * 0.8))
    board_x = int(width * 0.05)
    board_y = int(height * 0.1)
    tile_size = board_size_px // BOARD_SIZE

    # Draw board tiles
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            tile = state.board[y][x]
            color = TILE_COLORS.get(tile.type, TILE_COLORS[TileType.EMPTY])
            rect = pygame.Rect(board_x + x * tile_size, board_y + y * tile_size, tile_size, tile_size)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, GRID_COLOR, rect, 1)

    # Draw players
    for player_id, player in state.players.items():
        px = board_x + player.pos.x * tile_size + tile_size // 2
        py = board_y + player.pos.y * tile_size + tile_size // 2
        pygame.draw.circle(screen, PLAYER_COLORS.get(player_id, (200, 200, 200)), (px, py), tile_size // 3)
        label = small_font.render(player_id, True, (10, 10, 10))
        screen.blit(label, (px - 8, py - 8))

    # Top bar
    top_text = f"Round {state.round}/{state.max_rounds}  |  {'PAUSED' if paused else 'RUNNING'}  |  Speed {seconds_per_round:.1f}s"
    screen.blit(font.render(top_text, True, TEXT_COLOR), (board_x, board_y - 30))

    # Scoreboard (right panel)
    right_x = int(width * 0.7)
    right_y = int(height * 0.1)
    screen.blit(font.render("Scoreboard", True, TEXT_COLOR), (right_x, right_y))
    offset = 30
    for player_id, player in sorted(state.players.items()):
        line = f"{player_id}  score={player.score}  keys={player.keys}"
        screen.blit(small_font.render(line, True, PLAYER_COLORS.get(player_id, TEXT_COLOR)), (right_x, right_y + offset))
        offset += 20

    # Active deals (right panel)
    deal_y = right_y + offset + 10
    screen.blit(small_font.render("Deals", True, TEXT_COLOR), (right_x, deal_y))
    if state.active_deals:
        for i, deal in enumerate(state.active_deals[:4]):
            summary = f"{deal.from_player}->{deal.to_player} {deal.status}"
            screen.blit(small_font.render(summary, True, TEXT_COLOR), (right_x, deal_y + 18 + i * 16))
    else:
        screen.blit(small_font.render("None", True, TEXT_COLOR), (right_x, deal_y + 18))

    # Event ticker (bottom)
    ticker_y = int(height * 0.85)
    screen.blit(font.render("Events", True, TEXT_COLOR), (board_x, ticker_y))
    for i, line in enumerate(event_log[-6:]):
        screen.blit(small_font.render(line, True, TEXT_COLOR), (board_x, ticker_y + 20 + i * 18))
