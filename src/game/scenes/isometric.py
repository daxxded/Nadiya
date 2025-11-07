"""Isometric helpers and simple map layout rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

import pygame

from game.config import COLORS, TILE_HEIGHT, TILE_WIDTH


@dataclass
class Tile:
    kind: str
    walkable: bool


class IsometricGrid:
    def __init__(self, width: int, height: int, default_tile: Tile) -> None:
        self.width = width
        self.height = height
        self.tiles: List[List[Tile]] = [[default_tile for _ in range(width)] for _ in range(height)]

    def set_row(self, y: int, tiles: Sequence[Tile]) -> None:
        for x, tile in enumerate(tiles):
            if x < self.width:
                self.tiles[y][x] = tile

    def tile_at(self, grid_pos: Tuple[int, int]) -> Tile:
        x, y = grid_pos
        return self.tiles[y][x]


FLOOR_TILE = Tile("floor", True)
BLOCK_TILE = Tile("block", False)


def iso_to_screen(grid_x: int, grid_y: int, origin: Tuple[int, int]) -> Tuple[int, int]:
    ox, oy = origin
    screen_x = (grid_x - grid_y) * TILE_WIDTH // 2 + ox
    screen_y = (grid_x + grid_y) * TILE_HEIGHT // 2 + oy
    return screen_x, screen_y


def draw_tile(surface: pygame.Surface, position: Tuple[int, int], color: Tuple[int, int, int]) -> None:
    cx, cy = position
    points = [
        (cx, cy - TILE_HEIGHT // 2),
        (cx + TILE_WIDTH // 2, cy),
        (cx, cy + TILE_HEIGHT // 2),
        (cx - TILE_WIDTH // 2, cy)
    ]
    pygame.draw.polygon(surface, color, points)
    pygame.draw.polygon(surface, COLORS.warm_dark, points, 2)


class IsoCharacter(pygame.sprite.Sprite):
    def __init__(self, color: Tuple[int, int, int]) -> None:
        super().__init__()
        self.color = color
        self.grid_pos = pygame.math.Vector2(1, 1)
        self.speed = 4.0
        self.image = pygame.Surface((TILE_WIDTH // 2, TILE_HEIGHT), pygame.SRCALPHA)
        pygame.draw.ellipse(self.image, color, self.image.get_rect())
        self.rect = self.image.get_rect()

    def move(self, direction: pygame.math.Vector2, dt: float, grid: IsometricGrid) -> None:
        target = self.grid_pos + direction * self.speed * dt
        target_grid = (int(round(target.x)), int(round(target.y)))
        if 0 <= target_grid[0] < grid.width and 0 <= target_grid[1] < grid.height:
            if grid.tile_at(target_grid).walkable:
                self.grid_pos = pygame.math.Vector2(target_grid)

    def screen_position(self, origin: Tuple[int, int]) -> Tuple[int, int]:
        return iso_to_screen(int(self.grid_pos.x), int(self.grid_pos.y), origin)


__all__ = ["IsometricGrid", "IsoCharacter", "iso_to_screen", "draw_tile", "FLOOR_TILE", "BLOCK_TILE"]
