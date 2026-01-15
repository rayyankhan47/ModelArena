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

    # Event ticker (bottom)
    ticker_y = int(height * 0.85)
    screen.blit(font.render("Events", True, TEXT_COLOR), (board_x, ticker_y))
    for i, line in enumerate(event_log[-6:]):
        screen.blit(small_font.render(line, True, TEXT_COLOR), (board_x, ticker_y + 20 + i * 18))
"""Pygame application loop for AI Arena."""

import random
import time
from typing import Dict, List, Tuple

import pygame

from ai_arena.engine.generate import generate_initial_state
from ai_arena.engine.reducer import resolve_round
from ai_arena.engine.types import (
    Action,
    CollectAction,
    Coord,
    GameState,
    MoveAction,
    NoopAction,
    OpenVaultAction,
    ScanAction,
    SetTrapAction,
    StealAction,
    TileType,
)
from ai_arena.ui.render import COLORS, draw_board, draw_event_log, draw_sidebar


def run_pygame(seed: str, rounds: int, speed: float, fullscreen: bool = True):
    """Run a live demo match using random agents."""
    pygame.init()
    pygame.display.set_caption("AI Arena - Grid Heist")

    if fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((1280, 720))

    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 18)
    small_font = pygame.font.SysFont("Arial", 14)

    state = generate_initial_state(seed=seed, max_rounds=rounds)
    events_log: List[str] = []

    paused = False
    step_once = False
    speed_multiplier = max(0.25, speed)
    last_tick = time.time()

    while True:
        # Input handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return
                if event.key == pygame.K_SPACE:
                    paused = not paused
                if event.key == pygame.K_RIGHT:
                    step_once = True
                if event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    speed_multiplier = min(4.0, speed_multiplier + 0.25)
                if event.key == pygame.K_MINUS:
                    speed_multiplier = max(0.25, speed_multiplier - 0.25)

        screen.fill(COLORS["background"])

        # Layout regions
        width, height = screen.get_size()
        sidebar_rect = pygame.Rect(width - 300, 0, 300, height - 160)
        board_rect = pygame.Rect(0, 0, width - 300, height - 160)
        events_rect = pygame.Rect(0, height - 160, width, 160)

        # Draw current state
        draw_board(screen, state, board_rect, font)
        draw_sidebar(screen, state, sidebar_rect, font, small_font)
        draw_event_log(screen, events_log, events_rect, small_font)

        pygame.display.flip()

        # Control pacing
        if paused and not step_once:
            clock.tick(30)
            continue

        now = time.time()
        if now - last_tick < (1.0 / speed_multiplier):
            clock.tick(60)
            continue
        last_tick = now

        if state.round >= state.max_rounds:
            paused = True
            step_once = False
            continue

        # Generate random actions
        actions = _generate_random_actions(state)
        result = resolve_round(state, actions)
        state = result.next_state

        # Update event log
        for event in result.events[-8:]:
            events_log.append(_format_event(event.kind, event.payload))

        step_once = False

        clock.tick(60)


def _generate_random_actions(state: GameState) -> Dict[str, Action]:
    """Generate random legal actions for each player."""
    actions: Dict[str, Action] = {}
    for player_id in state.players.keys():
        if state.players[player_id].trapped_for > 0:
            actions[player_id] = NoopAction(reason="trapped")
            continue
        candidates = _list_action_candidates(state, player_id)
        actions[player_id] = random.choice(candidates) if candidates else NoopAction(reason="no_actions")
    return actions


def _list_action_candidates(state: GameState, player_id: str) -> List[Action]:
    """Build a list of concrete legal actions for a player."""
    player = state.players[player_id]
    pos = player.pos
    tile = state.board[pos.y][pos.x]
    actions: List[Action] = []

    # Move actions
    for direction, coord in _get_adjacent_directions(pos).items():
        if _is_valid_coord(coord, state):
            actions.append(MoveAction(dir=direction))

    # Collect
    if tile.type in [TileType.TREASURE_1, TileType.TREASURE_2, TileType.TREASURE_3, TileType.KEY]:
        actions.append(CollectAction())

    # Open vault
    if tile.type == TileType.VAULT and player.keys > 0:
        actions.append(OpenVaultAction())

    # Scan
    if tile.type == TileType.SCANNER:
        actions.append(ScanAction())

    # Set trap
    for direction, coord in _get_adjacent_directions(pos).items():
        if _is_valid_coord(coord, state):
            if state.board[coord[1]][coord[0]].type == TileType.EMPTY:
                actions.append(SetTrapAction(dir=direction))

    # Steal
    for other_id, other_player in state.players.items():
        if other_id == player_id:
            continue
        if _is_adjacent(pos, other_player.pos):
            actions.append(StealAction(target_player_id=other_id))

    # Noop fallback
    actions.append(NoopAction())

    return actions


def _get_adjacent_directions(pos: Coord) -> Dict[str, Tuple[int, int]]:
    return {
        "N": (pos.x, pos.y - 1),
        "E": (pos.x + 1, pos.y),
        "S": (pos.x, pos.y + 1),
        "W": (pos.x - 1, pos.y),
    }


def _is_valid_coord(coord: Tuple[int, int], state: GameState) -> bool:
    return 0 <= coord[0] < len(state.board[0]) and 0 <= coord[1] < len(state.board)


def _is_adjacent(a: Coord, b: Coord) -> bool:
    return abs(a.x - b.x) + abs(a.y - b.y) == 1


def _format_event(kind: str, payload: Dict) -> str:
    if "player_id" in payload:
        return f"{payload['player_id']}: {kind}"
    return kind
