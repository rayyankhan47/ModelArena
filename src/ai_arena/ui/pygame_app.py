"""Pygame visualization for AI Arena (Grid Heist)."""

import sys
import time
import random
from pathlib import Path
from typing import Dict, List, Tuple

import pygame

from ai_arena.engine.generate import generate_initial_state
from ai_arena.engine.reducer import resolve_round
from ai_arena.engine.rules import legal_actions
from ai_arena.storage.logger import MatchReplay
from ai_arena.engine.types import (
    ActionType,
    BoardTile,
    CollectAction,
    Coord,
    GameState,
    MoveAction,
    NoopAction,
    OpenVaultAction,
    PlayerState,
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

PLAYER_NAMES = {
    "P1": "GPT-4",
    "P2": "Claude",
    "P3": "Gemini",
    "P4": "GPT-3.5",
}

PLAYER_ASSETS = {
    "P1": "gpt4.png",
    "P2": "claude.jpeg",
    "P3": "gemini.png",
    "P4": "gpt3p5.png",
}

PHASES = [
    ("A", "Snapshot"),
    ("B", "Planning"),
    ("C", "Negotiation"),
    ("D", "Commit"),
    ("E", "Resolve"),
    ("F", "Memory"),
]

PHASE_STEP_SECONDS = 1.5
NEGOTIATION_STEP_SECONDS = 0.6


def run_demo(seed: str = "demo_1", rounds: int = 15, speed: float = 1.0, fullscreen: bool = True):
    """Run a live demo with phase-by-phase controls and a clean UI."""
    pygame.init()

    if fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((1400, 900))

    pygame.display.set_caption("AI Arena - Grid Heist")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 18)
    small_font = pygame.font.SysFont("Arial", 14)
    heading_font = pygame.font.SysFont("Arial", 22, bold=True)

    state = generate_initial_state(seed=seed, max_rounds=rounds)
    event_log: List[str] = []
    selected_agent = "P1"
    drawer_open = False
    started = False
    autoplay = False
    match_over = False
    phase_index = 0
    phase_started_at = time.time()
    negotiation_messages: List[Dict[str, str]] = []
    negotiation_index = 0
    pending_actions = None
    stats = _init_match_stats()
    player_icons = _load_player_icons()
    phase_step_seconds = max(0.4, PHASE_STEP_SECONDS / max(speed, 0.1))
    negotiation_step_seconds = max(0.2, NEGOTIATION_STEP_SECONDS / max(speed, 0.1))
    layout: Dict[str, object] = {}

    def enter_phase(new_index: int) -> None:
        nonlocal negotiation_messages, negotiation_index, pending_actions, state, match_over, phase_started_at
        phase_name = PHASES[new_index][1]
        if phase_name == "Negotiation":
            negotiation_messages = _build_demo_negotiation_messages(state, state.round)
            negotiation_index = 0
        if phase_name == "Commit":
            pending_actions = _select_random_actions(state)
        if phase_name == "Resolve":
            if pending_actions is None:
                pending_actions = _select_random_actions(state)
            result = resolve_round(state, pending_actions)
            state = result.next_state
            _append_events(result.events, event_log, stats)
            pending_actions = None
            if state.round >= state.max_rounds:
                match_over = True
        phase_started_at = time.time()

    def advance_phase() -> None:
        nonlocal phase_index, negotiation_index, phase_started_at
        if not started or match_over:
            return
        phase_name = PHASES[phase_index][1]
        if phase_name == "Negotiation" and negotiation_index < len(negotiation_messages):
            negotiation_index += 1
            phase_started_at = time.time()
            return
        phase_index = (phase_index + 1) % len(PHASES)
        enter_phase(phase_index)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit(0)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if not started:
                    if layout.get("play_button") and layout["play_button"].collidepoint(pos):
                        started = True
                        enter_phase(phase_index)
                    continue
                if layout.get("autoplay_button") and layout["autoplay_button"].collidepoint(pos):
                    if started and not match_over:
                        autoplay = not autoplay
                        phase_started_at = time.time()
                if layout.get("next_button") and layout["next_button"].collidepoint(pos):
                    advance_phase()
                if layout.get("agent_icons"):
                    for pid, rect in layout["agent_icons"].items():
                        if rect.collidepoint(pos):
                            selected_agent = pid
                            drawer_open = True
                            break
                if drawer_open and layout.get("drawer_rect") and not layout["drawer_rect"].collidepoint(pos):
                    drawer_open = False

        now = time.time()
        if autoplay and started and not match_over:
            phase_name = PHASES[phase_index][1]
            if phase_name == "Negotiation":
                if negotiation_index < len(negotiation_messages):
                    if now - phase_started_at >= negotiation_step_seconds:
                        negotiation_index += 1
                        phase_started_at = now
                else:
                    if now - phase_started_at >= phase_step_seconds:
                        advance_phase()
            else:
                if now - phase_started_at >= phase_step_seconds:
                    advance_phase()

        layout = _render_frame(
            screen=screen,
            state=state,
            event_log=event_log,
            font=font,
            small_font=small_font,
            heading_font=heading_font,
            started=started,
            autoplay=autoplay,
            match_over=match_over,
            phase_index=phase_index,
            negotiation_messages=negotiation_messages,
            negotiation_index=negotiation_index,
            selected_agent=selected_agent,
            drawer_open=drawer_open,
            player_icons=player_icons,
            stats=stats,
            phase_context=None,
        )
        pygame.display.flip()
        clock.tick(60)


def run_replay_ui(match_id: str, db_path: str = "ai_arena.db", speed: float = 1.0, fullscreen: bool = True):
    """Replay a Backboard match with phase-by-phase controls and real agent data."""
    replay = MatchReplay(db_path)
    match_info = replay.get_match_info(match_id)
    if not match_info:
        raise ValueError(f"Match {match_id} not found")

    pygame.init()
    if fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((1400, 900))

    pygame.display.set_caption(f"AI Arena - Replay {match_id}")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 18)
    small_font = pygame.font.SysFont("Arial", 14)
    heading_font = pygame.font.SysFont("Arial", 22, bold=True)

    total_rounds = replay.get_round_count(match_id)
    state = generate_initial_state(seed=match_info["seed"], max_rounds=match_info["max_rounds"])
    round_index = 0
    phase_index = 0
    started = True
    autoplay = False
    match_over = False
    phase_started_at = time.time()
    phase_step_seconds = max(0.4, PHASE_STEP_SECONDS / max(speed, 0.1))
    negotiation_step_seconds = max(0.2, NEGOTIATION_STEP_SECONDS / max(speed, 0.1))

    selected_agent = "P1"
    drawer_open = False
    player_icons = _load_player_icons()
    stats = _init_match_stats()
    event_log: List[str] = []
    negotiation_messages: List[Dict[str, str]] = []
    negotiation_index = 0
    round_data: Dict[str, object] | None = None
    phase_context: Dict[str, Dict[str, object]] | None = None
    layout: Dict[str, object] = {}

    def load_round_context(round_num: int) -> None:
        nonlocal round_data, negotiation_messages, negotiation_index, phase_context
        if round_num >= total_rounds:
            round_data = None
            negotiation_messages = []
            negotiation_index = 0
            phase_context = None
            return
        round_data = replay.get_round_data(match_id, round_num)
        agent_calls = {
            pid: replay.get_agent_calls_for_round(match_id, round_num, pid)
            for pid in PLAYER_NAMES.keys()
        }
        tool_calls = replay.get_tool_calls_for_round(match_id, round_num)
        memory_summaries = replay.get_memory_summaries_for_round(match_id, round_num)
        phase_context = _build_phase_context(agent_calls, tool_calls, memory_summaries, round_data or {})
        negotiation_messages = _build_negotiation_from_calls(agent_calls, round_num)
        negotiation_index = 0

    def advance_phase() -> None:
        nonlocal phase_index, negotiation_index, phase_started_at, round_index, state, match_over
        if match_over:
            return
        phase_name = PHASES[phase_index][1]
        if phase_name == "Negotiation" and negotiation_index < len(negotiation_messages):
            negotiation_index += 1
            phase_started_at = time.time()
            return
        if phase_name == "Resolve":
            if round_data and round_data.get("events"):
                _append_events(round_data["events"], event_log, stats)
            if round_data and round_data.get("state"):
                state = _state_from_dict(round_data["state"])
        if phase_name == "Memory":
            round_index += 1
            if round_index >= total_rounds:
                match_over = True
                return
            load_round_context(round_index)
        phase_index = (phase_index + 1) % len(PHASES)
        phase_started_at = time.time()

    load_round_context(round_index)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit(0)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if autoplay and match_over:
                    autoplay = False
                if layout.get("autoplay_button") and layout["autoplay_button"].collidepoint(pos):
                    if not match_over:
                        autoplay = not autoplay
                        phase_started_at = time.time()
                if layout.get("next_button") and layout["next_button"].collidepoint(pos):
                    advance_phase()
                if layout.get("agent_icons"):
                    for pid, rect in layout["agent_icons"].items():
                        if rect.collidepoint(pos):
                            selected_agent = pid
                            drawer_open = True
                            break
                if drawer_open and layout.get("drawer_rect") and not layout["drawer_rect"].collidepoint(pos):
                    drawer_open = False

        now = time.time()
        if autoplay and not match_over:
            phase_name = PHASES[phase_index][1]
            if phase_name == "Negotiation":
                if negotiation_index < len(negotiation_messages):
                    if now - phase_started_at >= negotiation_step_seconds:
                        negotiation_index += 1
                        phase_started_at = now
                else:
                    if now - phase_started_at >= phase_step_seconds:
                        advance_phase()
            else:
                if now - phase_started_at >= phase_step_seconds:
                    advance_phase()

        display_state = state
        if PHASES[phase_index][1] in ["Resolve", "Memory"] and round_data and round_data.get("state"):
            display_state = _state_from_dict(round_data["state"])

        layout = _render_frame(
            screen=screen,
            state=display_state,
            event_log=event_log,
            font=font,
            small_font=small_font,
            heading_font=heading_font,
            started=started,
            autoplay=autoplay,
            match_over=match_over,
            phase_index=phase_index,
            negotiation_messages=negotiation_messages,
            negotiation_index=negotiation_index,
            selected_agent=selected_agent,
            drawer_open=drawer_open,
            player_icons=player_icons,
            stats=stats,
            phase_context=phase_context,
        )
        pygame.display.flip()
        clock.tick(60)

def _select_random_actions(state: GameState) -> Dict[str, object]:
    """Select varied random actions for demo agents to showcase all game mechanics."""
    actions: Dict[str, object] = {}
    for player_id, player in state.players.items():
        if player.trapped_for > 0:
            actions[player_id] = NoopAction(reason="trapped")
            continue

        tile = state.board[player.pos.y][player.pos.x]
        
        # Prioritize interesting actions to showcase game mechanics
        action_priority = []
        
        # High priority: open vault if possible (big reward)
        if tile.type == TileType.VAULT and player.keys > 0:
            action_priority.append(OpenVaultAction())
        
        # High priority: steal if adjacent to another player
        for other_id, other_player in state.players.items():
            if other_id != player_id and _is_adjacent(player.pos, other_player.pos):
                if random.random() < 0.3:  # 30% chance to steal when adjacent
                    action_priority.append(StealAction(target_player_id=other_id))
                    break
        
        # Medium priority: collect treasure/key
        if tile.type in [TileType.TREASURE_1, TileType.TREASURE_2, TileType.TREASURE_3, TileType.KEY]:
            action_priority.append(CollectAction())
        
        # Medium priority: scan on scanner tiles
        if tile.type == TileType.SCANNER and random.random() < 0.5:
            action_priority.append(ScanAction())
        
        # Low priority: set trap if we have keys (defensive play)
        if player.keys > 0 and random.random() < 0.2:
            for direction in ["N", "E", "S", "W"]:
                trap_action = SetTrapAction(dir=direction)
                if _is_action_legal(state, player_id, trap_action):
                    action_priority.append(trap_action)
                    break
        
        # Try prioritized actions first
        selected = None
        for act in action_priority:
            if _is_action_legal(state, player_id, act):
                selected = act
                break
        
        # Fallback to movement
        if selected is None:
            move_dirs = ["N", "E", "S", "W"]
            random.shuffle(move_dirs)
            for direction in move_dirs:
                move_act = MoveAction(dir=direction)
                if _is_action_legal(state, player_id, move_act):
                    selected = move_act
                    break
        
        actions[player_id] = selected if selected else NoopAction()
    return actions


def _is_adjacent(pos1, pos2) -> bool:
    """Check if two positions are adjacent."""
    return abs(pos1.x - pos2.x) + abs(pos1.y - pos2.y) == 1


def _is_action_legal(state: GameState, player_id: str, action: object) -> bool:
    """Lightweight legality check using existing rule summaries."""
    action_type = getattr(action, "type", None)
    if action_type is None:
        return False

    player = state.players[player_id]
    tile = state.board[player.pos.y][player.pos.x]

    if action_type == ActionType.MOVE.value and isinstance(action, MoveAction):
        dest = _apply_direction(player.pos.x, player.pos.y, action.dir)
        return _in_bounds(state, dest)
    if action_type == ActionType.COLLECT.value:
        return tile.type in [
            TileType.TREASURE_1,
            TileType.TREASURE_2,
            TileType.TREASURE_3,
            TileType.KEY,
        ]
    if action_type == ActionType.OPEN_VAULT.value:
        return tile.type == TileType.VAULT and player.keys > 0
    if action_type == ActionType.SCAN.value:
        return tile.type == TileType.SCANNER
    if action_type == ActionType.SET_TRAP.value and isinstance(action, SetTrapAction):
        dest = _apply_direction(player.pos.x, player.pos.y, action.dir)
        if not _in_bounds(state, dest):
            return False
        return state.board[dest[1]][dest[0]].type == TileType.EMPTY
    if action_type == ActionType.STEAL.value and isinstance(action, StealAction):
        target = state.players.get(action.target_player_id)
        if not target:
            return False
        return abs(player.pos.x - target.pos.x) + abs(player.pos.y - target.pos.y) == 1
    if action_type == ActionType.NOOP.value:
        return True

    return False


def _apply_direction(x: int, y: int, direction: str) -> Tuple[int, int]:
    if direction == "N":
        return x, y - 1
    if direction == "E":
        return x + 1, y
    if direction == "S":
        return x, y + 1
    if direction == "W":
        return x - 1, y
    return x, y


def _in_bounds(state: GameState, coord: Tuple[int, int]) -> bool:
    return 0 <= coord[0] < len(state.board[0]) and 0 <= coord[1] < len(state.board)


def _render_frame(
    screen,
    state: GameState,
    event_log: List[str],
    font,
    small_font,
    heading_font,
    started: bool,
    autoplay: bool,
    match_over: bool,
    phase_index: int,
    negotiation_messages: List[Dict[str, str]],
    negotiation_index: int,
    selected_agent: str,
    drawer_open: bool,
    player_icons: Dict[str, pygame.Surface],
    stats: Dict[str, Dict[str, int]],
    phase_context: Dict[str, Dict[str, object]] | None = None,
) -> Dict[str, object]:
    screen.fill(WINDOW_BG)
    width, height = screen.get_size()
    layout: Dict[str, object] = {"agent_icons": {}}

    margin = 24
    header_h = 70
    board_size_px = min(int(width * 0.55), int(height * 0.65))
    board_x = margin
    board_y = header_h + 20
    tile_size = board_size_px // BOARD_SIZE
    panel_x = board_x + board_size_px + 32
    panel_y = header_h
    panel_w = max(280, width - panel_x - margin)
    panel_h = height - panel_y - margin

    phase_code, phase_name = PHASES[phase_index]
    current_round = min(state.round + 1, state.max_rounds)

    title = "AI Arena — Grid Heist"
    screen.blit(heading_font.render(title, True, TEXT_COLOR), (margin, 18))
    sub = f"Round {current_round} of {state.max_rounds} · Phase {phase_code}: {phase_name}"
    screen.blit(font.render(sub, True, TEXT_COLOR), (margin, 44))

    # Controls
    next_label = "Next Message" if phase_name == "Negotiation" and negotiation_index < len(negotiation_messages) else "Next Phase"
    next_rect = pygame.Rect(panel_x, 18, 140, 28)
    auto_rect = pygame.Rect(panel_x + 150, 18, 160, 28)
    _draw_button(screen, next_rect, next_label, enabled=started and not match_over)
    auto_label = "Autoplay: On" if autoplay else "Autoplay: Off"
    _draw_button(screen, auto_rect, auto_label, active=autoplay, enabled=started and not match_over)
    layout["next_button"] = next_rect
    layout["autoplay_button"] = auto_rect

    # Board and tiles
    layout["agent_icons"].update(
        _draw_board(screen, state, board_x, board_y, tile_size, small_font, player_icons, selected_agent)
    )

    # Right panel background
    panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
    pygame.draw.rect(screen, (24, 24, 30), panel_rect)
    pygame.draw.rect(screen, (60, 60, 70), panel_rect, 2)

    # Scoreboard
    _draw_scoreboard(screen, state, panel_rect, font, small_font, player_icons)

    # Negotiation chat panel
    if started and phase_name == "Negotiation":
        _draw_chat_panel(
            screen,
            panel_rect,
            small_font,
            negotiation_messages[:negotiation_index],
        )

    # Event log and legend
    _draw_event_log(screen, event_log, small_font, board_x, board_y + board_size_px + 18)
    _draw_legend(screen, small_font, board_x, height - margin - 40)

    if drawer_open:
        drawer_rect = _draw_inspector_drawer(
            screen,
            state,
            selected_agent,
            phase_name,
            small_font,
            font,
            negotiation_messages[:negotiation_index],
            stats,
            phase_context,
        )
        layout["drawer_rect"] = drawer_rect

    if not started:
        layout["play_button"] = _draw_welcome_overlay(screen, heading_font, font, small_font)

    if match_over:
        _draw_end_overlay(screen, heading_font, font, small_font, state, stats)

    return layout


def _draw_board(
    screen,
    state: GameState,
    board_x: int,
    board_y: int,
    tile_size: int,
    font,
    player_icons: Dict[str, pygame.Surface],
    selected_agent: str,
) -> Dict[str, pygame.Rect]:
    hitboxes: Dict[str, pygame.Rect] = {}
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            tile = state.board[y][x]
            color = TILE_COLORS.get(tile.type, TILE_COLORS[TileType.EMPTY])
            rect = pygame.Rect(board_x + x * tile_size, board_y + y * tile_size, tile_size, tile_size)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, GRID_COLOR, rect, 1)
            label_text = _get_tile_label(tile.type)
            if label_text:
                label = font.render(label_text, True, (10, 10, 10))
                label_rect = label.get_rect(center=(rect.centerx, rect.centery))
                screen.blit(label, label_rect)

    for player_id, player in state.players.items():
        px = board_x + player.pos.x * tile_size + tile_size // 2
        py = board_y + player.pos.y * tile_size + tile_size // 2
        size = int(tile_size * 0.72)
        icon_rect = pygame.Rect(px - size // 2, py - size // 2, size, size)
        icon = player_icons.get(player_id)
        if icon is not None:
            scaled = pygame.transform.smoothscale(icon, (size, size))
            screen.blit(scaled, icon_rect)
        else:
            pygame.draw.rect(screen, PLAYER_COLORS.get(player_id, (200, 200, 200)), icon_rect, border_radius=6)
        if player_id == selected_agent:
            pygame.draw.rect(screen, (255, 255, 255), icon_rect, 2, border_radius=6)
        hitboxes[player_id] = icon_rect

    return hitboxes


def _draw_scoreboard(screen, state: GameState, panel_rect: pygame.Rect, font, small_font, icons):
    header = font.render("Scoreboard", True, TEXT_COLOR)
    screen.blit(header, (panel_rect.x + 16, panel_rect.y + 16))
    y = panel_rect.y + 46
    for player_id, player in sorted(state.players.items()):
        name = PLAYER_NAMES.get(player_id, player_id)
        icon = icons.get(player_id)
        if icon is not None:
            scaled = pygame.transform.smoothscale(icon, (24, 24))
            screen.blit(scaled, (panel_rect.x + 16, y))
        label = f"{name}  ·  {player.score} pts  ·  {player.keys} keys"
        screen.blit(small_font.render(label, True, TEXT_COLOR), (panel_rect.x + 48, y + 4))
        y += 30


def _draw_chat_panel(screen, panel_rect: pygame.Rect, font, messages: List[Dict[str, str]]):
    chat_rect = pygame.Rect(panel_rect.x + 16, panel_rect.y + 160, panel_rect.width - 32, panel_rect.height - 190)
    pygame.draw.rect(screen, (18, 18, 22), chat_rect)
    pygame.draw.rect(screen, (60, 60, 70), chat_rect, 1)
    title = font.render("Negotiation (public)", True, TEXT_COLOR)
    screen.blit(title, (chat_rect.x + 8, chat_rect.y + 8))
    y = chat_rect.y + 32
    for msg in messages[-8:]:
        speaker = msg.get("speaker", "Agent")
        text = msg.get("text", "")
        lines = _wrap_text(f"{speaker}: {text}", font, chat_rect.width - 16)
        for line in lines:
            if y > chat_rect.bottom - 20:
                break
            screen.blit(font.render(line, True, (210, 210, 220)), (chat_rect.x + 8, y))
            y += 18


def _draw_event_log(screen, event_log: List[str], font, x: int, y: int):
    title = font.render("Recent Events", True, TEXT_COLOR)
    screen.blit(title, (x, y))
    for idx, line in enumerate(event_log[-7:]):
        color = _event_color(line)
        screen.blit(font.render(line, True, color), (x, y + 20 + idx * 18))


def _draw_legend(screen, font, x: int, y: int):
    legend = "Legend: 1P=Treasure1  2P=Treasure2  3P=Treasure3  K=Key  V=Vault  SC=Scanner  TR=Trap"
    screen.blit(font.render(legend, True, (150, 150, 150)), (x, y))


def _draw_inspector_drawer(
    screen,
    state: GameState,
    selected_agent: str,
    phase_name: str,
    small_font,
    font,
    negotiation_messages: List[Dict[str, str]],
    stats: Dict[str, Dict[str, int]],
    phase_context: Dict[str, Dict[str, object]] | None = None,
) -> pygame.Rect:
    width, height = screen.get_size()
    drawer_w = min(360, int(width * 0.3))
    drawer_rect = pygame.Rect(width - drawer_w - 16, 100, drawer_w, height - 140)
    pygame.draw.rect(screen, (24, 24, 30), drawer_rect)
    pygame.draw.rect(screen, (60, 60, 70), drawer_rect, 2)

    name = PLAYER_NAMES.get(selected_agent, selected_agent)
    title = f"{name} · {selected_agent}"
    screen.blit(font.render(title, True, TEXT_COLOR), (drawer_rect.x + 16, drawer_rect.y + 16))

    player = state.players[selected_agent]
    lines = [
        f"Position: ({player.pos.x}, {player.pos.y})",
        f"Score: {player.score}",
        f"Keys: {player.keys}",
        f"Phase: {phase_name}",
        "",
    ]

    phase_lines = _phase_details(state, selected_agent, phase_name, negotiation_messages, phase_context)
    lines.extend(phase_lines)
    lines.append("")
    if phase_context and phase_context.get(selected_agent):
        ctx = phase_context[selected_agent]
        models = ctx.get("models")
        if isinstance(models, dict):
            model_parts = [f"{k}:{v}" for k, v in models.items() if v]
            if model_parts:
                lines.append("Models: " + ", ".join(model_parts))
        tools = ctx.get("tools")
        if tools:
            tool_names = ", ".join(tools[:4])
            lines.append(f"Tools used: {tool_names}")
        mem_shared = ctx.get("memory_shared")
        if mem_shared:
            lines.append("Shared memory: " + _truncate_text(mem_shared, 90))
        lines.append("")
    lines.append("Session stats:")
    lines.append(f"Treasure collected: {stats[selected_agent]['treasure']}")
    lines.append(f"Keys collected: {stats[selected_agent]['keys']}")
    lines.append(f"Vaults opened: {stats[selected_agent]['vaults']}")
    lines.append(f"Scans used: {stats[selected_agent]['scans']}")
    lines.append(f"Traps set: {stats[selected_agent]['traps']}")
    lines.append(f"Steals: {stats[selected_agent]['steals']}")

    _draw_lines(screen, lines, drawer_rect.x + 16, drawer_rect.y + 50, small_font)
    return drawer_rect


def _draw_lines(screen, lines: List[str], x: int, y: int, font):
    offset = 0
    for line in lines:
        if line == "":
            offset += 8
            continue
        screen.blit(font.render(line, True, TEXT_COLOR), (x, y + offset))
        offset += 18


def _draw_button(screen, rect: pygame.Rect, label: str, active: bool = False, enabled: bool = True):
    bg = (52, 96, 160) if active else (40, 40, 52)
    if not enabled:
        bg = (30, 30, 38)
    pygame.draw.rect(screen, bg, rect, border_radius=6)
    pygame.draw.rect(screen, (80, 80, 90), rect, 1, border_radius=6)
    font = pygame.font.SysFont("Arial", 14)
    text_color = (220, 220, 230) if enabled else (120, 120, 130)
    label_surf = font.render(label, True, text_color)
    label_rect = label_surf.get_rect(center=rect.center)
    screen.blit(label_surf, label_rect)


def _draw_welcome_overlay(screen, heading_font, font, small_font) -> pygame.Rect:
    width, height = screen.get_size()
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    overlay.fill((10, 10, 14, 230))
    screen.blit(overlay, (0, 0))

    panel_w = int(width * 0.7)
    panel_h = int(height * 0.6)
    panel_rect = pygame.Rect((width - panel_w) // 2, (height - panel_h) // 2, panel_w, panel_h)
    pygame.draw.rect(screen, (24, 24, 30), panel_rect)
    pygame.draw.rect(screen, (80, 80, 90), panel_rect, 2)

    title = heading_font.render("Welcome to Grid Heist", True, TEXT_COLOR)
    screen.blit(title, (panel_rect.x + 24, panel_rect.y + 24))

    rules = (
        "Four AI agents compete on a 9x9 board. Collect treasures (1P/2P/3P), "
        "grab keys, and open vaults for big points. Scanners grant +1 point, traps "
        "skip the next action, and stealing lets you take a key or point from an adjacent rival."
    )
    lines = _wrap_text(rules, small_font, panel_w - 48)
    y = panel_rect.y + 70
    for line in lines:
        screen.blit(small_font.render(line, True, (200, 200, 210)), (panel_rect.x + 24, y))
        y += 18

    play_rect = pygame.Rect(panel_rect.x + 24, panel_rect.bottom - 60, 160, 36)
    _draw_button(screen, play_rect, "Play", enabled=True)
    return play_rect


def _draw_end_overlay(screen, heading_font, font, small_font, state: GameState, stats: Dict[str, Dict[str, int]]):
    width, height = screen.get_size()
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    overlay.fill((10, 10, 14, 220))
    screen.blit(overlay, (0, 0))

    panel_w = int(width * 0.6)
    panel_h = int(height * 0.5)
    panel_rect = pygame.Rect((width - panel_w) // 2, (height - panel_h) // 2, panel_w, panel_h)
    pygame.draw.rect(screen, (24, 24, 30), panel_rect)
    pygame.draw.rect(screen, (80, 80, 90), panel_rect, 2)

    winner_id = max(state.players.keys(), key=lambda pid: state.players[pid].score)
    winner_name = PLAYER_NAMES.get(winner_id, winner_id)
    title = heading_font.render(f"{winner_name} wins!", True, TEXT_COLOR)
    screen.blit(title, (panel_rect.x + 24, panel_rect.y + 24))

    y = panel_rect.y + 70
    for player_id, player in sorted(state.players.items()):
        name = PLAYER_NAMES.get(player_id, player_id)
        line = (
            f"{name}: {player.score} pts, {player.keys} keys, "
            f"{stats[player_id]['treasure']} treasure, {stats[player_id]['steals']} steals"
        )
        screen.blit(small_font.render(line, True, (210, 210, 220)), (panel_rect.x + 24, y))
        y += 22


def _wrap_text(text: str, font, max_width: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _phase_details(
    state: GameState,
    player_id: str,
    phase_name: str,
    messages: List[Dict[str, str]],
    phase_context: Dict[str, Dict[str, object]] | None,
) -> List[str]:
    context = phase_context.get(player_id) if phase_context else None
    if phase_name == "Snapshot":
        return ["Observing the board state and opponent positions."]
    if phase_name == "Planning":
        if context and context.get("planning"):
            return ["Planning next move.", _truncate_text(context["planning"], 120)]
        summary = _summarize_legal_actions(state, player_id)
        return ["Planning next move.", f"Legal actions now: {summary}"]
    if phase_name == "Negotiation":
        if context and context.get("negotiation"):
            return ["Negotiating with other agents.", _truncate_text(context["negotiation"], 120)]
        last_message = ""
        name = PLAYER_NAMES.get(player_id, player_id)
        for msg in messages:
            if msg.get("speaker") == name:
                last_message = msg.get("text", "")
        if last_message:
            return ["Negotiating with other agents.", f"Latest message: {last_message}"]
        return ["Negotiating with other agents."]
    if phase_name == "Commit":
        if context and context.get("commit"):
            return ["Committing the final action for this round.", _truncate_text(context["commit"], 120)]
        return ["Committing the final action for this round."]
    if phase_name == "Resolve":
        if context and context.get("resolve"):
            return ["Resolving actions and updating scores.", context["resolve"]]
        return ["Resolving actions and updating scores."]
    if phase_name == "Memory":
        if context and context.get("memory_private"):
            return ["Summarizing this round into memory.", _truncate_text(context["memory_private"], 120)]
        return ["Summarizing this round into memory."]
    return []


def _truncate_text(text: str, max_len: int) -> str:
    clean = " ".join(text.split())
    if len(clean) <= max_len:
        return clean
    return clean[: max_len - 1].rstrip() + "…"


def _summarize_legal_actions(state: GameState, player_id: str) -> str:
    summaries = legal_actions(state, player_id)
    types = []
    for summary in summaries:
        if summary.type not in types:
            types.append(summary.type)
    return ", ".join(t.replace("_", " ").title() for t in types) if types else "None"


def _get_tile_label(tile_type: TileType) -> str:
    labels = {
        TileType.TREASURE_1: "1P",
        TileType.TREASURE_2: "2P",
        TileType.TREASURE_3: "3P",
        TileType.KEY: "K",
        TileType.VAULT: "V",
        TileType.SCANNER: "SC",
        TileType.TRAP: "TR",
    }
    return labels.get(tile_type, "")


def _event_color(event_line: str) -> Tuple[int, int, int]:
    if "treasure" in event_line or "key" in event_line:
        return (120, 200, 120)
    if "vault" in event_line:
        return (190, 160, 230)
    if "steal" in event_line:
        return (230, 150, 150)
    if "trap" in event_line:
        return (230, 110, 110)
    if "scanner" in event_line:
        return (150, 200, 230)
    if "blocked" in event_line or "illegal" in event_line:
        return (190, 190, 190)
    return TEXT_COLOR


def _load_player_icons() -> Dict[str, pygame.Surface]:
    assets_dir = Path(__file__).resolve().parents[2] / "assets"
    icons: Dict[str, pygame.Surface] = {}
    for pid, filename in PLAYER_ASSETS.items():
        path = assets_dir / filename
        if path.exists():
            icons[pid] = pygame.image.load(str(path)).convert_alpha()
        else:
            icons[pid] = None
    return icons


def _build_demo_negotiation_messages(state: GameState, round_num: int) -> List[Dict[str, str]]:
    messages = [
        {"speaker": "Moderator", "text": f"Round {round_num + 1} negotiation begins. Keep it brief."},
    ]
    for pid, player in state.players.items():
        name = PLAYER_NAMES.get(pid, pid)
        if player.keys > 0:
            text = "I have a key. Open to trade for safe passage."
        elif player.score >= 4:
            text = "Leading on points. Propose a temporary non-aggression."
        else:
            text = "Looking for a vault key. Will return favors later."
        messages.append({"speaker": name, "text": text})
    return messages


def _init_match_stats() -> Dict[str, Dict[str, int]]:
    return {
        pid: {"treasure": 0, "keys": 0, "vaults": 0, "scans": 0, "traps": 0, "steals": 0}
        for pid in PLAYER_NAMES.keys()
    }


def _append_events(events, event_log: List[str], stats: Dict[str, Dict[str, int]]) -> None:
    for ev in events:
        line = _format_event(ev)
        if line:
            event_log.append(line)
        _update_stats(ev, stats)
    event_log[:] = event_log[-7:]


def _state_from_dict(state_dict: Dict[str, object]) -> GameState:
    try:
        return GameState.model_validate(state_dict)
    except Exception:
        # Fallback for older pydantic environments
        board = [
            [BoardTile(type=TileType(tile["type"])) for tile in row]
            for row in state_dict.get("board", [])
        ]
        players = {}
        for pid, pdata in (state_dict.get("players") or {}).items():
            pos = pdata.get("pos") or {}
            players[pid] = PlayerState(
                player_id=pdata.get("player_id", pid),
                pos=Coord(x=pos.get("x", 0), y=pos.get("y", 0)),
                score=pdata.get("score", 0),
                keys=pdata.get("keys", 0),
                trapped_for=pdata.get("trapped_for", 0),
            )
        return GameState(
            round=state_dict.get("round", 0),
            max_rounds=state_dict.get("max_rounds", 15),
            seed=state_dict.get("seed", "replay"),
            board=board,
            players=players,
            active_deals=state_dict.get("active_deals") or [],
        )


def _build_phase_context(
    agent_calls: Dict[str, List[Dict[str, object]]],
    tool_calls: List[Dict[str, object]],
    memory_summaries: List[Dict[str, object]],
    round_data: Dict[str, object],
) -> Dict[str, Dict[str, object]]:
    context: Dict[str, Dict[str, object]] = {pid: {"models": {}, "tools": []} for pid in PLAYER_NAMES.keys()}

    for pid, calls in agent_calls.items():
        for call in calls:
            phase = call.get("phase", "")
            model = call.get("model", "")
            if phase and model:
                context[pid]["models"][phase] = model
            content = _extract_response_text(call.get("response", {}))
            if phase.startswith("plan"):
                context[pid]["planning"] = content
            elif phase.startswith("negotiate"):
                context[pid]["negotiation"] = content
            elif phase.startswith("commit"):
                context[pid]["commit"] = content

    for summary in memory_summaries:
        pid = summary.get("player_id")
        if pid in context:
            context[pid]["memory_private"] = summary.get("private_summary", "")
            context[pid]["memory_shared"] = summary.get("shared_summary", "")

    for call in tool_calls:
        pid = call.get("player_id")
        name = call.get("tool_name", "")
        if pid in context and name:
            context[pid]["tools"].append(name)

    rewards = round_data.get("rewards", {}) if round_data else {}
    if isinstance(rewards, dict):
        for pid in context:
            if pid in rewards:
                context[pid]["resolve"] = f"Reward delta: {rewards.get(pid, 0)}"

    return context


def _build_negotiation_from_calls(
    agent_calls: Dict[str, List[Dict[str, object]]],
    round_num: int,
) -> List[Dict[str, str]]:
    messages = [{"speaker": "Moderator", "text": f"Round {round_num + 1} negotiation begins."}]
    for pid in PLAYER_NAMES.keys():
        calls = agent_calls.get(pid, [])
        text = ""
        for call in calls:
            phase = call.get("phase", "")
            if phase.startswith("negotiate"):
                text = _extract_response_text(call.get("response", {}))
                break
        if text:
            messages.append({"speaker": PLAYER_NAMES.get(pid, pid), "text": text})
    return messages


def _extract_response_text(response: object) -> str:
    if isinstance(response, dict):
        content = response.get("content")
        if isinstance(content, list):
            return " ".join(str(item) for item in content)
        if content:
            return str(content)
        message = response.get("message") or response.get("output")
        if message:
            return str(message)
    return str(response) if response else ""
def _event_value(ev, key: str, default=None):
    if isinstance(ev, dict):
        return ev.get(key, default)
    return getattr(ev, key, default)


def _format_event(ev) -> str:
    payload = _event_value(ev, "payload", {}) or {}
    player_id = payload.get("player_id", "?")
    player_name = PLAYER_NAMES.get(player_id, player_id)
    kind = _event_value(ev, "kind", "")
    round_num = _event_value(ev, "round", "?")
    if kind == "collect_treasure":
        value = payload.get("value", 0)
        return f"R{round_num}: {player_name} collected treasure (+{value})"
    if kind == "collect_key":
        return f"R{round_num}: {player_name} collected a key"
    if kind == "open_vault":
        return f"R{round_num}: {player_name} opened a vault (+8)"
    if kind == "scan_used":
        return f"R{round_num}: {player_name} used a scanner (+1)"
    if kind == "trap_set":
        return f"R{round_num}: {player_name} set a trap"
    if kind == "trap_triggered":
        return f"R{round_num}: {player_name} triggered a trap"
    if kind == "steal_key":
        target = PLAYER_NAMES.get(payload.get("target", "?"), payload.get("target", "?"))
        return f"R{round_num}: {player_name} stole a key from {target}"
    if kind == "steal_point":
        target = PLAYER_NAMES.get(payload.get("target", "?"), payload.get("target", "?"))
        return f"R{round_num}: {player_name} stole 1 point from {target}"
    if kind == "steal_fail":
        target = PLAYER_NAMES.get(payload.get("target", "?"), payload.get("target", "?"))
        return f"R{round_num}: {player_name} failed to steal from {target}"
    if kind == "collision_blocked":
        return f"R{round_num}: {player_name} was blocked by a collision"
    if kind == "move_blocked":
        return f"R{round_num}: {player_name} move blocked (occupied)"
    if kind == "illegal_action":
        return f"R{round_num}: {player_name} attempted an illegal action"
    if kind == "trapped_noop":
        return f"R{round_num}: {player_name} is trapped"
    return ""


def _update_stats(ev, stats: Dict[str, Dict[str, int]]) -> None:
    payload = _event_value(ev, "payload", {}) or {}
    player_id = payload.get("player_id")
    kind = _event_value(ev, "kind", "")
    if player_id not in stats:
        return
    if kind == "collect_treasure":
        stats[player_id]["treasure"] += 1
    if kind == "collect_key":
        stats[player_id]["keys"] += 1
    if kind == "open_vault":
        stats[player_id]["vaults"] += 1
    if kind == "scan_used":
        stats[player_id]["scans"] += 1
    if kind == "trap_set":
        stats[player_id]["traps"] += 1
    if kind in ["steal_key", "steal_point"]:
        stats[player_id]["steals"] += 1
