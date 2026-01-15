"""Pygame rendering helpers for AI Arena."""

from typing import Dict, List, Tuple

import pygame

from ai_arena.engine.types import GameState, TileType


COLORS = {
    "background": (18, 18, 22),
    "panel": (28, 28, 36),
    "grid": (45, 45, 58),
    "text": (235, 235, 245),
    "muted": (160, 160, 175),
    "highlight": (95, 180, 255),
    "P1": (235, 90, 90),
    "P2": (90, 220, 140),
    "P3": (90, 160, 235),
    "P4": (230, 200, 90),
}


TILE_COLORS = {
    TileType.EMPTY: (28, 28, 36),
    TileType.TREASURE_1: (180, 140, 60),
    TileType.TREASURE_2: (205, 160, 70),
    TileType.TREASURE_3: (230, 190, 85),
    TileType.KEY: (120, 200, 220),
    TileType.VAULT: (160, 120, 230),
    TileType.SCANNER: (120, 180, 120),
    TileType.TRAP: (200, 90, 120),
}


def draw_text(surface, text, pos, font, color, align="topleft"):
    """Draw text to surface with basic alignment."""
    rendered = font.render(text, True, color)
    rect = rendered.get_rect()
    setattr(rect, align, pos)
    surface.blit(rendered, rect)


def draw_board(
    surface,
    state: GameState,
    area_rect: pygame.Rect,
    font,
):
    """Draw the board and player tokens."""
    board_size = len(state.board)
    cell_size = min(area_rect.width, area_rect.height) // board_size

    board_origin_x = area_rect.x + (area_rect.width - cell_size * board_size) // 2
    board_origin_y = area_rect.y + (area_rect.height - cell_size * board_size) // 2

    # Draw grid and tiles
    for y in range(board_size):
        for x in range(board_size):
            tile = state.board[y][x]
            rect = pygame.Rect(
                board_origin_x + x * cell_size,
                board_origin_y + y * cell_size,
                cell_size,
                cell_size,
            )
            pygame.draw.rect(surface, TILE_COLORS[tile.type], rect)
            pygame.draw.rect(surface, COLORS["grid"], rect, 1)

    # Draw players
    for player_id, player in state.players.items():
        color = COLORS.get(player_id, COLORS["highlight"])
        center_x = board_origin_x + player.pos.x * cell_size + cell_size // 2
        center_y = board_origin_y + player.pos.y * cell_size + cell_size // 2
        pygame.draw.circle(surface, color, (center_x, center_y), cell_size // 3)
        draw_text(
            surface,
            player_id,
            (center_x, center_y),
            font,
            COLORS["background"],
            align="center",
        )


def draw_sidebar(
    surface,
    state: GameState,
    area_rect: pygame.Rect,
    font,
    small_font,
):
    """Draw scoreboard and metadata panel."""
    pygame.draw.rect(surface, COLORS["panel"], area_rect)

    draw_text(
        surface,
        "Scoreboard",
        (area_rect.x + 16, area_rect.y + 12),
        font,
        COLORS["text"],
    )

    y_offset = area_rect.y + 50
    for player_id in sorted(state.players.keys()):
        player = state.players[player_id]
        color = COLORS.get(player_id, COLORS["highlight"])
        pygame.draw.circle(surface, color, (area_rect.x + 28, y_offset + 8), 8)
        draw_text(
            surface,
            f"{player_id}  Score: {player.score}  Keys: {player.keys}",
            (area_rect.x + 48, y_offset),
            small_font,
            COLORS["text"],
        )
        y_offset += 28

    draw_text(
        surface,
        f"Round {state.round}/{state.max_rounds}",
        (area_rect.x + 16, area_rect.bottom - 40),
        small_font,
        COLORS["muted"],
    )


def draw_event_log(
    surface,
    events: List[str],
    area_rect: pygame.Rect,
    font,
):
    """Draw recent event log entries."""
    pygame.draw.rect(surface, COLORS["panel"], area_rect)
    draw_text(
        surface,
        "Recent Events",
        (area_rect.x + 12, area_rect.y + 8),
        font,
        COLORS["text"],
    )

    y = area_rect.y + 34
    for entry in events[-6:]:
        draw_text(
            surface,
            entry,
            (area_rect.x + 12, y),
            font,
            COLORS["muted"],
        )
        y += 22
