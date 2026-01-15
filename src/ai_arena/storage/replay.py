"""Replay system for AI Arena matches stored in database."""

import time
from typing import Dict, Any, List, Optional

from .logger import MatchReplay
from ..engine.generate import generate_initial_state
from ..engine.types import GameState
from ..ui.pygame_app import run_demo


def replay_match(match_id: str, speed: float = 1.0, db_path: str = "ai_arena.db") -> None:
    """Replay a match from database using Pygame visualization.

    Args:
        match_id: ID of the match to replay
        speed: Playback speed multiplier (1.0 = normal speed)
        db_path: Path to the database file
    """
    replay = MatchReplay(db_path)

    # Get match info
    match_info = replay.get_match_info(match_id)
    if not match_info:
        raise ValueError(f"Match {match_id} not found")

    print(f"Replaying match {match_id} (seed: {match_info['seed']})")

    # Generate initial state for replay
    initial_state = generate_initial_state(
        seed=match_info["seed"],
        max_rounds=match_info["max_rounds"]
    )

    # Get all round data
    round_count = replay.get_round_count(match_id)
    if round_count == 0:
        raise ValueError(f"No rounds found for match {match_id}")

    print(f"Match has {round_count} rounds")

    # Run replay with custom round generator
    run_replay_loop(match_id, initial_state, round_count, speed, replay)


def run_replay_loop(match_id: str, initial_state: GameState, round_count: int, speed: float, replay: MatchReplay):
    """Run the replay loop with Pygame, stepping through stored rounds."""
    import pygame
    import sys

    pygame.init()

    # Use fullscreen like the main demo
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_caption(f"AI Arena - Replay {match_id}")

    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 18)
    small_font = pygame.font.SysFont("Arial", 14)

    # Get screen dimensions
    width, height = screen.get_size()

    # Layout regions (same as main demo)
    board_size_px = min(int(width * 0.6), int(height * 0.8))
    board_x = int(width * 0.05)
    board_y = int(height * 0.1)
    tile_size = board_size_px // 9  # BOARD_SIZE = 9

    # Colors (same as main demo)
    WINDOW_BG = (18, 18, 22)
    GRID_COLOR = (40, 40, 48)
    TEXT_COLOR = (230, 230, 240)
    TILE_COLORS = {
        "empty": (30, 30, 36),
        "treasure_1": (64, 160, 96),
        "treasure_2": (50, 140, 200),
        "treasure_3": (200, 160, 80),
        "key": (210, 190, 60),
        "vault": (120, 80, 160),
        "scanner": (80, 140, 160),
        "trap": (140, 60, 60),
    }
    PLAYER_COLORS = {
        "P1": (220, 90, 90),
        "P2": (90, 160, 220),
        "P3": (90, 200, 140),
        "P4": (200, 180, 80),
    }

    # Replay state
    current_round = 0
    paused = False
    step_round = False
    last_tick = time.time()
    seconds_per_round = max(0.2, 1.0 / speed)

    event_log: List[str] = []
    tool_log: List[str] = []
    show_tools = True

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
                if event.key == pygame.K_t:
                    show_tools = not show_tools

        now = time.time()
        if current_round >= round_count:
            paused = True

        # Advance to next round if conditions met
        if (not paused or step_round) and current_round < round_count and (now - last_tick) >= seconds_per_round:
            current_round += 1
            event_log.clear()
            tool_log.clear()

            # Load round data
            round_data = replay.get_round_data(match_id, current_round)
            if round_data:
                # Convert stored state back to displayable format
                state_dict = round_data["state"]
                events = round_data.get("events", [])

                # Format events for display
                for event in events[-6:]:
                    event_log.append(f"R{event['round']}: {event['kind']} {event['payload']}")

                # Tool calls for this round
                tool_calls = replay.get_tool_calls_for_round(match_id, current_round)
                for call in tool_calls[:6]:
                    tool_log.append(f"{call['player_id']} {call['tool_name']}")

            last_tick = now
            step_round = False

        # Render current state
        screen.fill(WINDOW_BG)

        # Get current round data for rendering
        if current_round > 0:
            round_data = replay.get_round_data(match_id, current_round)
            if round_data:
                state_dict = round_data["state"]

                # Draw board
                board = state_dict["board"]
                for y in range(9):
                    for x in range(9):
                        tile = board[y][x]
                        color = TILE_COLORS.get(tile["type"], TILE_COLORS["empty"])
                        rect = pygame.Rect(board_x + x * tile_size, board_y + y * tile_size, tile_size, tile_size)
                        pygame.draw.rect(screen, color, rect)
                        pygame.draw.rect(screen, GRID_COLOR, rect, 1)

                # Draw players
                players = state_dict["players"]
                for player_id, player in players.items():
                    px = board_x + player["pos"]["x"] * tile_size + tile_size // 2
                    py = board_y + player["pos"]["y"] * tile_size + tile_size // 2
                    pygame.draw.circle(screen, PLAYER_COLORS.get(player_id, (200, 200, 200)), (px, py), tile_size // 3)
                    label = small_font.render(player_id, True, (10, 10, 10))
                    screen.blit(label, (px - 8, py - 8))

                # Top bar
                top_text = f"Replay: Round {current_round}/{round_count}  |  {'PAUSED' if paused else 'PLAYING'}  |  Speed {seconds_per_round:.1f}s"
                screen.blit(font.render(top_text, True, TEXT_COLOR), (board_x, board_y - 30))

                # Scoreboard (right panel)
                right_x = int(width * 0.7)
                right_y = int(height * 0.1)
                screen.blit(font.render("Scoreboard", True, TEXT_COLOR), (right_x, right_y))
                offset = 30
                for player_id in sorted(players.keys()):
                    player = players[player_id]
                    line = f"{player_id}  score={player['score']}  keys={player['keys']}"
                    screen.blit(small_font.render(line, True, PLAYER_COLORS.get(player_id, TEXT_COLOR)), (right_x, right_y + offset))
                    offset += 20

                # Tool calls (right panel, below scoreboard)
                if show_tools:
                    tool_y = right_y + offset + 10
                    screen.blit(small_font.render("Tool Calls", True, TEXT_COLOR), (right_x, tool_y))
                    for i, line in enumerate(tool_log[:6]):
                        screen.blit(small_font.render(line, True, TEXT_COLOR), (right_x, tool_y + 18 + i * 16))

                # Event ticker (bottom)
                ticker_y = int(height * 0.85)
                screen.blit(font.render("Events", True, TEXT_COLOR), (board_x, ticker_y))
                for i, line in enumerate(event_log[-6:]):
                    screen.blit(small_font.render(line, True, TEXT_COLOR), (board_x, ticker_y + 20 + i * 18))
        else:
            # Show initial state before any rounds
            top_text = f"Replay: Round 0/{round_count}  |  {'PAUSED' if paused else 'PLAYING'}  |  Speed {seconds_per_round:.1f}s"
            screen.blit(font.render(top_text, True, TEXT_COLOR), (board_x, board_y - 30))

            # Draw initial board
            board = initial_state.board
            for y in range(9):
                for x in range(9):
                    tile = board[y][x]
                    color = TILE_COLORS.get(tile.type.value, TILE_COLORS["empty"])
                    rect = pygame.Rect(board_x + x * tile_size, board_y + y * tile_size, tile_size, tile_size)
                    pygame.draw.rect(screen, color, rect)
                    pygame.draw.rect(screen, GRID_COLOR, rect, 1)

            # Draw initial players
            for player_id, player in initial_state.players.items():
                px = board_x + player.pos.x * tile_size + tile_size // 2
                py = board_y + player.pos.y * tile_size + tile_size // 2
                pygame.draw.circle(screen, PLAYER_COLORS.get(player_id, (200, 200, 200)), (px, py), tile_size // 3)
                label = small_font.render(player_id, True, (10, 10, 10))
                screen.blit(label, (px - 8, py - 8))

        pygame.display.flip()
        clock.tick(60)