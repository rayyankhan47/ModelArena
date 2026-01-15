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
                # Format events more readably
                player_id = ev.payload.get("player_id", "?")
                if ev.kind == "collect_treasure":
                    value = ev.payload.get("value", 0)
                    event_log.append(f"R{ev.round}: {player_id} collected treasure (+{value} pts)")
                elif ev.kind == "collect_key":
                    event_log.append(f"R{ev.round}: {player_id} collected a key")
                elif ev.kind == "open_vault":
                    event_log.append(f"R{ev.round}: {player_id} opened vault (+8 pts!)")
                elif ev.kind == "scan_used":
                    event_log.append(f"R{ev.round}: {player_id} used scanner (+1 pt)")
                elif ev.kind == "trap_set":
                    event_log.append(f"R{ev.round}: {player_id} set a trap")
                elif ev.kind == "trap_triggered":
                    event_log.append(f"R{ev.round}: {player_id} triggered a trap!")
                elif ev.kind == "steal_key":
                    target = ev.payload.get("target", "?")
                    event_log.append(f"R{ev.round}: {player_id} stole key from {target}")
                elif ev.kind == "steal_point":
                    target = ev.payload.get("target", "?")
                    event_log.append(f"R{ev.round}: {player_id} stole 1 pt from {target}")
                elif ev.kind == "steal_fail":
                    target = ev.payload.get("target", "?")
                    event_log.append(f"R{ev.round}: {player_id} failed to steal from {target}")
                elif ev.kind == "collision_blocked":
                    event_log.append(f"R{ev.round}: {player_id} blocked by collision")
                elif ev.kind == "illegal_action":
                    event_log.append(f"R{ev.round}: {player_id} illegal action")
                elif ev.kind == "trapped_noop":
                    event_log.append(f"R{ev.round}: {player_id} is trapped (no action)")
                else:
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

    # Draw board tiles with labels
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            tile = state.board[y][x]
            color = TILE_COLORS.get(tile.type, TILE_COLORS[TileType.EMPTY])
            rect = pygame.Rect(board_x + x * tile_size, board_y + y * tile_size, tile_size, tile_size)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, GRID_COLOR, rect, 1)
            
            # Add tile labels for clarity
            if tile.type != TileType.EMPTY:
                label_text = _get_tile_label(tile.type)
                if label_text:
                    label = small_font.render(label_text, True, (10, 10, 10))
                    label_rect = label.get_rect(center=(rect.centerx, rect.centery))
                    screen.blit(label, label_rect)

    # Draw players
    for player_id, player in state.players.items():
        px = board_x + player.pos.x * tile_size + tile_size // 2
        py = board_y + player.pos.y * tile_size + tile_size // 2
        pygame.draw.circle(screen, PLAYER_COLORS.get(player_id, (200, 200, 200)), (px, py), tile_size // 3)
        label = small_font.render(player_id, True, (10, 10, 10))
        screen.blit(label, (px - 8, py - 8))

    # Agent dock
    _draw_agent_dock(screen, selected_agent, small_font)

    # Top bar with game explanation
    if not pitch_mode:
        top_text = f"Round {state.round}/{state.max_rounds}  |  {'PAUSED' if paused else 'RUNNING'}  |  Speed {seconds_per_round:.1f}s"
        screen.blit(font.render(top_text, True, TEXT_COLOR), (board_x, board_y - 30))
        
        # Game explanation
        help_text = "Grid Heist: Collect treasures/keys, open vaults (+8 pts), set traps, steal from others. Highest score wins!"
        screen.blit(small_font.render(help_text, True, (150, 150, 150)), (board_x, board_y - 50))

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

    # Event ticker (bottom) with better formatting
    if not pitch_mode:
        ticker_y = int(height * 0.85)
        screen.blit(font.render("Recent Events", True, TEXT_COLOR), (board_x, ticker_y))
        for i, line in enumerate(event_log[-6:]):
            # Color code events for better visibility
            color = _get_event_color(line)
            screen.blit(small_font.render(line, True, color), (board_x, ticker_y + 20 + i * 18))
        
        # Add legend/help text
        legend_y = int(height * 0.92)
        legend_text = "Tiles: Green=Treasure1, Blue=Treasure2, Orange=Treasure3, Yellow=Key, Purple=Vault, Cyan=Scanner, Red=Trap"
        screen.blit(small_font.render(legend_text, True, (150, 150, 150)), (board_x, legend_y))

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


def _get_tile_label(tile_type: TileType) -> str:
    """Get a short label for a tile type."""
    labels = {
        TileType.TREASURE_1: "T1",
        TileType.TREASURE_2: "T2",
        TileType.TREASURE_3: "T3",
        TileType.KEY: "K",
        TileType.VAULT: "V",
        TileType.SCANNER: "S",
        TileType.TRAP: "!",
    }
    return labels.get(tile_type, "")


def _get_event_color(event_line: str) -> Tuple[int, int, int]:
    """Get color for an event line based on its type."""
    if "collect_treasure" in event_line or "collect_key" in event_line:
        return (100, 200, 100)  # Green for collections
    if "open_vault" in event_line:
        return (200, 150, 255)  # Purple for vaults
    if "steal" in event_line:
        return (255, 150, 150)  # Red for steals
    if "trap" in event_line:
        return (255, 100, 100)  # Bright red for traps
    if "scan" in event_line:
        return (150, 200, 255)  # Cyan for scans
    if "collision" in event_line or "illegal" in event_line:
        return (200, 200, 200)  # Gray for errors
    return TEXT_COLOR  # Default


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
