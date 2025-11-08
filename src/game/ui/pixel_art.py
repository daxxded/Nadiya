"""Procedurally generated pixel art sprites and backgrounds."""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, Iterable, List, Tuple

import pygame

from game.config import COLORS

Color = Tuple[int, int, int, int] | Tuple[int, int, int]


def _decode_pattern(pattern: Iterable[str], palette: Dict[str, Color], scale: int = 4) -> pygame.Surface:
    rows = [row.rstrip("\n") for row in pattern]
    height = len(rows)
    width = max(len(row) for row in rows)
    surface = pygame.Surface((width * scale, height * scale), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, key in enumerate(row):
            if key == " ":
                continue
            color = palette.get(key)
            if not color:
                continue
            rect = pygame.Rect(x * scale, y * scale, scale, scale)
            surface.fill(color, rect)
    return surface


@lru_cache(maxsize=16)
def nadiya_sprite() -> pygame.Surface:
    palette = {
        "H": (78, 54, 39, 255),  # hair
        "S": (241, 211, 187, 255),  # skin
        "T": (117, 171, 204, 255),  # top
        "J": (54, 72, 99, 255),  # jeans
        "B": (33, 33, 46, 255),  # shoes
        "C": (255, 178, 62, 255),  # accent
    }
    pattern = [
        "   HH   ",
        "  HHHH  ",
        " HHHHHH ",
        " HSSSSH ",
        "HSSSSSSH",
        "HSSSSSSH",
        " HSSSSH ",
        "  TTTT  ",
        "  TTTT  ",
        "  TCC T ",
        "  JJJJ  ",
        "  JJJJ  ",
        " JJ  JJ ",
        " BB  BB ",
    ]
    return _decode_pattern(pattern, palette, scale=4)


def classmate_variants() -> List[pygame.Surface]:
    base_pattern = [
        "   HH   ",
        "  HHHH  ",
        " HHHHHH ",
        " HSSSSH ",
        "HSSSSSSH",
        " HSSSSH ",
        "  TTTT  ",
        "  TTTT  ",
        "  PPPP  ",
        "  PPPP  ",
        " PP  PP ",
        " BB  BB ",
    ]
    palettes = [
        {"H": (58, 34, 12, 255), "S": (216, 188, 164, 255), "T": (208, 90, 90, 255), "P": (65, 96, 120, 255), "B": (33, 33, 46, 255)},
        {"H": (24, 48, 82, 255), "S": (235, 206, 178, 255), "T": (132, 192, 90, 255), "P": (100, 70, 50, 255), "B": (44, 36, 52, 255)},
        {"H": (96, 24, 64, 255), "S": (190, 160, 210, 255), "T": (255, 183, 75, 255), "P": (40, 56, 82, 255), "B": (30, 30, 30, 255)},
    ]
    sprites: List[pygame.Surface] = []
    for palette in palettes:
        sprite = _decode_pattern(base_pattern, palette, scale=4)
        sprites.append(sprite)
    return sprites


@lru_cache(maxsize=4)
def mom_sprite() -> pygame.Surface:
    palette = {
        "H": (46, 30, 20, 255),
        "S": (238, 208, 186, 255),
        "D": (132, 90, 120, 255),
        "B": (44, 44, 54, 255),
    }
    pattern = [
        "  HHHH  ",
        " HHHHHH ",
        " HSSSSH ",
        " HSSSSH ",
        "  DDDD  ",
        "  DDDD  ",
        "  DDDD  ",
        "  DDDD  ",
        "  B  B  ",
    ]
    return _decode_pattern(pattern, palette, scale=4)


def draw_kitchen_background(surface: pygame.Surface) -> None:
    surface.fill((58, 46, 40))
    floor_color = (94, 80, 72)
    tile = pygame.Surface((32, 32))
    tile.fill(floor_color)
    darker = (80, 68, 60)
    pygame.draw.rect(tile, darker, tile.get_rect(), 2)
    for y in range(0, surface.get_height(), 32):
        for x in range(0, surface.get_width(), 32):
            surface.blit(tile, (x, y))
    counter_rect = pygame.Rect(120, 160, surface.get_width() - 240, 120)
    pygame.draw.rect(surface, (72, 56, 48), counter_rect)
    pygame.draw.rect(surface, (128, 102, 82), counter_rect.inflate(-16, -16))
    backsplash = pygame.Rect(counter_rect.left, counter_rect.top - 56, counter_rect.width, 48)
    pygame.draw.rect(surface, (66, 54, 58), backsplash)
    for i in range(counter_rect.left + 24, counter_rect.right - 24, 56):
        pygame.draw.rect(surface, (52, 40, 36), (i, counter_rect.bottom - 20, 32, 20))
    lamp_color = (255, 214, 170)
    for offset in range(0, counter_rect.width, 180):
        center = (counter_rect.left + 90 + offset, counter_rect.top - 20)
        pygame.draw.circle(surface, lamp_color, center, 12)
        pygame.draw.line(surface, lamp_color, (center[0], center[1] - 30), (center[0], center[1] - 60), 3)


def draw_school_background(surface: pygame.Surface) -> None:
    surface.fill((32, 34, 52))
    floor = pygame.Rect(0, surface.get_height() // 3, surface.get_width(), surface.get_height() * 2 // 3)
    pygame.draw.rect(surface, (64, 76, 96), floor)
    pygame.draw.rect(surface, (48, 60, 80), floor.inflate(-40, 0))
    locker_color = (52, 88, 132)
    for i in range(6):
        locker = pygame.Rect(60 + i * 120, 80, 100, 160)
        pygame.draw.rect(surface, locker_color, locker)
        pygame.draw.rect(surface, (34, 60, 92), locker, 4)
        handle = pygame.Rect(locker.centerx + 20, locker.centery - 10, 10, 40)
        pygame.draw.rect(surface, (230, 230, 240), handle)
    banner = pygame.Rect(surface.get_width() // 2 - 200, 40, 400, 36)
    pygame.draw.rect(surface, COLORS.accent_fries, banner)
    font = pygame.font.Font(None, 24)
    text = font.render("Sprachschule — Keep Shouting German", True, COLORS.text_dark)
    surface.blit(text, (banner.centerx - text.get_width() // 2, banner.centery - text.get_height() // 2))


def draw_living_room_background(surface: pygame.Surface) -> None:
    surface.fill((38, 30, 40))
    rug = pygame.Rect(surface.get_width() // 2 - 220, surface.get_height() - 220, 440, 180)
    pygame.draw.ellipse(surface, (86, 60, 78), rug)
    couch = pygame.Rect(surface.get_width() // 2 - 260, surface.get_height() - 300, 520, 140)
    pygame.draw.rect(surface, (104, 68, 88), couch, border_radius=24)
    pygame.draw.rect(surface, (124, 88, 110), couch.inflate(-30, -30), border_radius=20)
    lamp = pygame.Rect(surface.get_width() - 140, surface.get_height() - 320, 30, 140)
    pygame.draw.rect(surface, (200, 172, 136), lamp)
    pygame.draw.circle(surface, (255, 230, 180), (lamp.centerx + 10, lamp.top - 20), 22)


__all__ = [
    "nadiya_sprite",
    "mom_sprite",
    "classmate_variants",
    "draw_kitchen_background",
    "draw_school_background",
    "draw_living_room_background",
]
