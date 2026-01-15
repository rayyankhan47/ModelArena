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

TAB_NAMES = ["Summary", "Memory", "Routing", "Tools", "RAG/Search", "Negotiation"]


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
    selected_agent = "P1"
    drawer_open = False
    active_tab = 0
    pitch_mode = False

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
                if event.key == pygame.K_1:
                    selected_agent = "P1"
                    drawer_open = True
                if event.key == pygame.K_2:
                    selected_agent = "P2"
                    drawer_open = True
                if event.key == pygame.K_3:
                    selected_agent = "P3"
                    drawer_open = True
                if event.key == pygame.K_4:
                    selected_agent = "P4"
                    drawer_open = True
                if event.key == pygame.K_i:
                    drawer_open = not drawer_open
                if event.key == pygame.K_p:
                    pitch_mode = not pitch_mode
                if event.key == pygame.K_TAB:
                    active_tab = (active_tab + 1) % len(TAB_NAMES)
                if event.key == pygame.K_MINUS:
                    seconds_per_round = min(5.0, seconds_per_round + 0.2)
                if event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    seconds_per_round = max(0.1, seconds_per_round - 0.2)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked_agent = _hit_test_agent_icons(event.pos)
                if clicked_agent:
                    selected_agent = clicked_agent
                    drawer_open = True

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

        _render_frame(
            screen,
            state,
            event_log,
            font,
            small_font,
            paused,
            seconds_per_round,
            selected_agent,
            drawer_open,
            active_tab,
            pitch_mode,
        )
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


def _render_frame(
    screen,
    state: GameState,
    event_log: List[str],
    font,
    small_font,
    paused: bool,
    seconds_per_round: float,
    selected_agent: str,
    drawer_open: bool,
    active_tab: int,
    pitch_mode: bool,
):
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

    # Agent dock
    _draw_agent_dock(screen, selected_agent, small_font)

    # Top bar
    if not pitch_mode:
        top_text = f"Round {state.round}/{state.max_rounds}  |  {'PAUSED' if paused else 'RUNNING'}  |  Speed {seconds_per_round:.1f}s"
        screen.blit(font.render(top_text, True, TEXT_COLOR), (board_x, board_y - 30))

    # Scoreboard (right panel)
    right_x = int(width * 0.7)
    right_y = int(height * 0.1)
    if not pitch_mode:
        screen.blit(font.render("Scoreboard", True, TEXT_COLOR), (right_x, right_y))
    offset = 30
    for player_id, player in sorted(state.players.items()):
        line = f"{player_id}  score={player.score}  keys={player.keys}"
        screen.blit(small_font.render(line, True, PLAYER_COLORS.get(player_id, TEXT_COLOR)), (right_x, right_y + offset))
        offset += 20

    if not pitch_mode:
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
    if not pitch_mode:
        ticker_y = int(height * 0.85)
        screen.blit(font.render("Events", True, TEXT_COLOR), (board_x, ticker_y))
        for i, line in enumerate(event_log[-6:]):
            screen.blit(small_font.render(line, True, TEXT_COLOR), (board_x, ticker_y + 20 + i * 18))

    if drawer_open:
        _draw_inspector_drawer(screen, state, selected_agent, active_tab, font, small_font)

    if pitch_mode:
        _draw_pitch_banner(screen, small_font)


def _draw_agent_dock(screen, selected_agent: str, font):
    width, _ = screen.get_size()
    dock_x = int(width * 0.05)
    dock_y = 12
    for idx, pid in enumerate(["P1", "P2", "P3", "P4"]):
        color = PLAYER_COLORS.get(pid, TEXT_COLOR)
        rect = pygame.Rect(dock_x + idx * 36, dock_y, 28, 28)
        pygame.draw.rect(screen, color, rect, border_radius=6)
        if pid == selected_agent:
            pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=6)
        label = font.render(pid, True, (10, 10, 10))
        screen.blit(label, (rect.x + 4, rect.y + 4))


def _draw_inspector_drawer(screen, state: GameState, selected_agent: str, active_tab: int, font, small_font):
    width, height = screen.get_size()
    drawer_w = int(width * 0.28)
    rect = pygame.Rect(width - drawer_w, 0, drawer_w, height)
    pygame.draw.rect(screen, (24, 24, 30), rect)
    pygame.draw.rect(screen, (60, 60, 70), rect, 2)

    title = f"{selected_agent} Inspector"
    screen.blit(font.render(title, True, TEXT_COLOR), (rect.x + 16, rect.y + 16))

    # Tabs
    tab_y = rect.y + 52
    for idx, name in enumerate(TAB_NAMES):
        label = f"[{idx+1}] {name}"
        color = (255, 255, 255) if idx == active_tab else TEXT_COLOR
        screen.blit(small_font.render(label, True, color), (rect.x + 16, tab_y + idx * 18))

    # Content
    content_y = tab_y + len(TAB_NAMES) * 18 + 10
    content_x = rect.x + 16

    if active_tab == 0:
        _draw_lines(
            screen,
            [
                f"Score: {state.players[selected_agent].score}",
                f"Keys: {state.players[selected_agent].keys}",
                f"Pos: ({state.players[selected_agent].pos.x},{state.players[selected_agent].pos.y})",
                "Last action: demo",
                "Reward delta: demo",
            ],
            content_x,
            content_y,
            small_font,
        )
    elif active_tab == 1:
        _draw_lines(screen, ["Memory summary: demo", "Recent memory: demo"], content_x, content_y, small_font)
    elif active_tab == 2:
        _draw_lines(screen, ["Planner model: demo", "Actor model: demo"], content_x, content_y, small_font)
    elif active_tab == 3:
        _draw_lines(screen, ["Tool calls: demo"], content_x, content_y, small_font)
    elif active_tab == 4:
        _draw_lines(screen, ["Citations: demo", "SearchQuery: demo"], content_x, content_y, small_font)
    elif active_tab == 5:
        _draw_lines(screen, ["Last negotiation: demo"], content_x, content_y, small_font)


def _draw_lines(screen, lines: List[str], x: int, y: int, font):
    for i, line in enumerate(lines):
        screen.blit(font.render(line, True, TEXT_COLOR), (x, y + i * 18))


def _draw_pitch_banner(screen, font):
    width, _ = screen.get_size()
    banner = "Pitch Mode: Memory + Routing + Tools + RAG + Search"
    rect = pygame.Rect(int(width * 0.2), 8, int(width * 0.6), 28)
    pygame.draw.rect(screen, (40, 70, 120), rect, border_radius=6)
    screen.blit(font.render(banner, True, (240, 240, 240)), (rect.x + 10, rect.y + 6))


def _hit_test_agent_icons(pos) -> str:
    x, y = pos
    width, _ = pygame.display.get_surface().get_size()
    dock_x = int(width * 0.05)
    dock_y = 12
    for idx, pid in enumerate(["P1", "P2", "P3", "P4"]):
        rect = pygame.Rect(dock_x + idx * 36, dock_y, 28, 28)
        if rect.collidepoint(x, y):
            return pid
    return ""
