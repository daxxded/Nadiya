"""Procedurally generated pixel art sprites and backgrounds."""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, Iterable, List, Sequence, Tuple

import pygame

from game.config import COLORS, TILE_HEIGHT, TILE_WIDTH

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
@lru_cache(maxsize=32)
def _iso_block_surface(
    width_tiles: int,
    depth_tiles: int,
    height_px: int,
    *,
    top: Color,
    left: Color,
    right: Color,
    outline: Color = (40, 32, 32, 200),
) -> pygame.Surface:
    width = width_tiles * TILE_WIDTH
    depth = depth_tiles * TILE_HEIGHT
    surface = pygame.Surface((width, depth + height_px), pygame.SRCALPHA)
    cx = width // 2
    half_depth = depth // 2
    top_poly = [
        (cx, 0),
        (width, half_depth),
        (cx, depth),
        (0, half_depth),
    ]
    left_poly = [
        (0, half_depth),
        (cx, depth),
        (cx, depth + height_px),
        (0, half_depth + height_px),
    ]
    right_poly = [
        (width, half_depth),
        (cx, depth),
        (cx, depth + height_px),
        (width, half_depth + height_px),
    ]
    pygame.draw.polygon(surface, left, left_poly)
    pygame.draw.polygon(surface, right, right_poly)
    pygame.draw.polygon(surface, top, top_poly)
    pygame.draw.lines(surface, outline, True, top_poly, 2)
    pygame.draw.lines(surface, outline, False, [left_poly[0], left_poly[1], left_poly[2], left_poly[3]], 2)
    pygame.draw.lines(surface, outline, False, [right_poly[0], right_poly[1], right_poly[2], right_poly[3]], 2)
    return surface


@lru_cache(maxsize=16)
def nadiya_idle_sprite() -> pygame.Surface:
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


@lru_cache(maxsize=4)
def nadiya_walk_cycle() -> Sequence[pygame.Surface]:
    palette = {
        "H": (78, 54, 39, 255),
        "S": (241, 211, 187, 255),
        "T": (117, 171, 204, 255),
        "J": (54, 72, 99, 255),
        "B": (33, 33, 46, 255),
        "C": (255, 178, 62, 255),
    }
    frames = [
        [
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
            "  J JJ  ",
            " JJ  JJ ",
            " BB  BB ",
        ],
        [
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
            "  JJ J  ",
            " JJ  JJ ",
            " BB  BB ",
        ],
        [
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
        ],
        [
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
            "  JJ JJ ",
            " JJ  JJ ",
            " BB  BB ",
        ],
    ]
    return tuple(_decode_pattern(pattern, palette, scale=4) for pattern in frames)


@lru_cache(maxsize=4)
def nadiya_eat_sprite() -> pygame.Surface:
    palette = {
        "H": (78, 54, 39, 255),
        "S": (241, 211, 187, 255),
        "T": (117, 171, 204, 255),
        "J": (54, 72, 99, 255),
        "B": (33, 33, 46, 255),
        "F": (255, 198, 64, 255),
    }
    pattern = [
        "   HH   ",
        "  HHHH  ",
        " HHHHHH ",
        " HSSSSH ",
        "HSSFFSSH",
        "HSSFFSSH",
        " HSSSSH ",
        "  TTTT  ",
        "  TTTT  ",
        "  TTTT  ",
        "  JJJJ  ",
        "  JJJJ  ",
        " JJ  JJ ",
        " BB  BB ",
    ]
    return _decode_pattern(pattern, palette, scale=4)


def nadiya_sprite() -> pygame.Surface:
    return nadiya_idle_sprite()


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


@lru_cache(maxsize=4)
def neighbor_sprite() -> pygame.Surface:
    palette = {
        "H": (92, 64, 44, 255),
        "S": (224, 196, 170, 255),
        "T": (150, 110, 180, 255),
        "P": (80, 104, 132, 255),
        "B": (36, 36, 46, 255),
    }
    pattern = [
        "  HHH  ",
        " HHHHH ",
        " HSSSH ",
        "HSSSSSH",
        " HSSSH ",
        "  TTT  ",
        "  TTT  ",
        "  PPP  ",
        "  PPP  ",
        "  B B  ",
    ]
    return _decode_pattern(pattern, palette, scale=4)


@lru_cache(maxsize=4)
def cat_sprite() -> pygame.Surface:
    palette = {
        "F": (120, 104, 96, 255),
        "S": (180, 164, 150, 255),
        "E": (240, 220, 200, 255),
    }
    pattern = [
        "  FF  ",
        " FSSF ",
        "FSSSSF",
        "FSSSSF",
        " FSSF ",
        "  FFF ",
        " FFF  ",
        "F F F ",
    ]
    return _decode_pattern(pattern, palette, scale=4)


@lru_cache(maxsize=8)
def plant_sprite() -> pygame.Surface:
    surface = pygame.Surface((96, 120), pygame.SRCALPHA)
    pot = _iso_block_surface(
        1,
        1,
        22,
        top=(150, 98, 70, 255),
        left=(120, 72, 50, 255),
        right=(176, 130, 90, 255),
    )
    surface.blit(pot, (16, 50))
    pygame.draw.circle(surface, (74, 132, 94, 255), (48, 38), 24)
    pygame.draw.circle(surface, (64, 112, 80, 255), (30, 42), 16)
    pygame.draw.circle(surface, (64, 112, 80, 255), (62, 48), 18)
    return surface


@lru_cache(maxsize=8)
def sofa_sprite() -> pygame.Surface:
    base = _iso_block_surface(
        2,
        1,
        36,
        top=(132, 88, 112, 255),
        left=(104, 68, 90, 255),
        right=(156, 120, 148, 255),
    )
    surface = pygame.Surface((base.get_width(), base.get_height() + 20), pygame.SRCALPHA)
    surface.blit(base, (0, 20))
    back = _iso_block_surface(
        2,
        1,
        56,
        top=(144, 96, 124, 255),
        left=(116, 76, 96, 255),
        right=(170, 132, 160, 255),
    )
    surface.blit(back, (0, 0))
    return surface


@lru_cache(maxsize=8)
def coffee_table_sprite() -> pygame.Surface:
    return _iso_block_surface(
        1,
        1,
        18,
        top=(168, 140, 116, 255),
        left=(128, 100, 80, 255),
        right=(188, 160, 132, 255),
    )


@lru_cache(maxsize=8)
def tv_stand_sprite() -> pygame.Surface:
    stand = _iso_block_surface(
        1,
        1,
        28,
        top=(82, 68, 72, 255),
        left=(58, 48, 52, 255),
        right=(102, 88, 92, 255),
    )
    surface = pygame.Surface((stand.get_width(), stand.get_height() + 36), pygame.SRCALPHA)
    surface.blit(stand, (0, 36))
    screen_rect = pygame.Rect(28, 8, stand.get_width() - 56, 40)
    pygame.draw.rect(surface, (24, 24, 32, 255), screen_rect)
    pygame.draw.rect(surface, (46, 56, 96, 255), screen_rect, 3)
    return surface


@lru_cache(maxsize=8)
def bookshelf_sprite() -> pygame.Surface:
    body = _iso_block_surface(
        1,
        1,
        72,
        top=(176, 142, 108, 255),
        left=(142, 108, 78, 255),
        right=(196, 164, 134, 255),
    )
    surface = pygame.Surface((body.get_width(), body.get_height()), pygame.SRCALPHA)
    surface.blit(body, (0, 0))
    for idx in range(3):
        shelf_y = 18 + idx * 24
        pygame.draw.line(surface, (128, 96, 66, 255), (20, shelf_y), (surface.get_width() - 20, shelf_y), 3)
    for column, color in enumerate([(216, 112, 120, 255), (108, 176, 128, 255), (96, 132, 204, 255)]):
        rect = pygame.Rect(34 + column * 18, 24, 14, 42)
        pygame.draw.rect(surface, color, rect)
    return surface


@lru_cache(maxsize=8)
def bed_sprite() -> pygame.Surface:
    frame = _iso_block_surface(
        2,
        2,
        36,
        top=(192, 180, 180, 255),
        left=(162, 140, 140, 255),
        right=(214, 198, 198, 255),
    )
    surface = pygame.Surface((frame.get_width(), frame.get_height() + 30), pygame.SRCALPHA)
    surface.blit(frame, (0, 30))
    headboard = _iso_block_surface(
        2,
        1,
        48,
        top=(150, 120, 130, 255),
        left=(120, 92, 102, 255),
        right=(176, 148, 158, 255),
    )
    surface.blit(headboard, (0, 0))
    pillow = pygame.Surface((64, 32), pygame.SRCALPHA)
    pygame.draw.ellipse(pillow, (248, 242, 236, 255), pillow.get_rect())
    surface.blit(pillow, (40, 50))
    surface.blit(pillow, (110, 56))
    return surface


@lru_cache(maxsize=8)
def wardrobe_sprite() -> pygame.Surface:
    return _iso_block_surface(
        1,
        1,
        82,
        top=(156, 132, 118, 255),
        left=(128, 102, 88, 255),
        right=(176, 152, 138, 255),
    )


@lru_cache(maxsize=8)
def desk_sprite() -> pygame.Surface:
    return _iso_block_surface(
        1,
        1,
        30,
        top=(168, 150, 126, 255),
        left=(130, 112, 94, 255),
        right=(192, 168, 140, 255),
    )


@lru_cache(maxsize=8)
def shower_sprite() -> pygame.Surface:
    cab = _iso_block_surface(
        1,
        1,
        82,
        top=(190, 210, 220, 180),
        left=(150, 180, 200, 160),
        right=(208, 230, 240, 180),
    )
    surface = pygame.Surface((cab.get_width(), cab.get_height()), pygame.SRCALPHA)
    surface.blit(cab, (0, 0))
    pygame.draw.line(surface, (200, 200, 220, 255), (surface.get_width() // 2, 20), (surface.get_width() // 2, 96), 3)
    return surface


@lru_cache(maxsize=8)
def sink_sprite() -> pygame.Surface:
    base = _iso_block_surface(
        1,
        1,
        24,
        top=(214, 214, 220, 255),
        left=(180, 180, 190, 255),
        right=(238, 238, 246, 255),
    )
    surface = pygame.Surface((base.get_width(), base.get_height()), pygame.SRCALPHA)
    surface.blit(base, (0, 0))
    pygame.draw.circle(surface, (180, 190, 200, 255), (surface.get_width() // 2, 26), 18, 3)
    return surface


@lru_cache(maxsize=8)
def fridge_sprite() -> pygame.Surface:
    return _iso_block_surface(
        1,
        1,
        84,
        top=(224, 232, 236, 255),
        left=(192, 202, 210, 255),
        right=(242, 248, 252, 255),
    )


@lru_cache(maxsize=8)
def stove_sprite() -> pygame.Surface:
    block = _iso_block_surface(
        1,
        1,
        44,
        top=(112, 112, 116, 255),
        left=(80, 80, 86, 255),
        right=(136, 136, 140, 255),
    )
    surface = pygame.Surface((block.get_width(), block.get_height()), pygame.SRCALPHA)
    surface.blit(block, (0, 0))
    pygame.draw.circle(surface, (200, 48, 48, 255), (surface.get_width() // 2, 24), 10, 2)
    return surface


@lru_cache(maxsize=8)
def counter_sprite() -> pygame.Surface:
    return _iso_block_surface(
        2,
        1,
        28,
        top=(188, 166, 142, 255),
        left=(148, 124, 104, 255),
        right=(210, 188, 164, 255),
    )


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


def draw_school_exterior(surface: pygame.Surface) -> None:
    surface.fill((46, 68, 86))
    sky = pygame.Rect(0, 0, surface.get_width(), surface.get_height() // 2)
    pygame.draw.rect(surface, (118, 168, 196), sky)
    ground = pygame.Rect(0, surface.get_height() // 2, surface.get_width(), surface.get_height() // 2)
    pygame.draw.rect(surface, (88, 108, 118), ground)
    building = pygame.Rect(surface.get_width() // 2 - 220, surface.get_height() // 2 - 80, 440, 160)
    pygame.draw.rect(surface, (164, 120, 130), building)
    for i in range(6):
        window = pygame.Rect(building.left + 30 + i * 70, building.top + 30, 48, 52)
        pygame.draw.rect(surface, (240, 240, 250), window)
    sign = pygame.Rect(building.centerx - 130, building.top + 110, 260, 28)
    pygame.draw.rect(surface, (54, 68, 84), sign)
    font = pygame.font.Font(None, 28)
    text = font.render("Sprachschule", True, (250, 232, 200))
    surface.blit(text, (sign.centerx - text.get_width() // 2, sign.centery - text.get_height() // 2))


def draw_school_hallway(surface: pygame.Surface) -> None:
    surface.fill((42, 40, 60))
    stripe = pygame.Rect(0, surface.get_height() // 2 - 40, surface.get_width(), 80)
    pygame.draw.rect(surface, (66, 62, 92), stripe)
    for i in range(8):
        door = pygame.Rect(80 + i * 120, stripe.top - 60, 70, 120)
        pygame.draw.rect(surface, (104, 92, 128), door)
        pygame.draw.rect(surface, (84, 70, 110), door, 6)


def draw_school_lobby(surface: pygame.Surface) -> None:
    surface.fill((48, 46, 70))
    board = pygame.Rect(surface.get_width() // 2 - 180, 80, 360, 140)
    pygame.draw.rect(surface, (68, 110, 140), board)
    font = pygame.font.Font(None, 32)
    text = font.render("Guten Morgen!", True, (250, 246, 230))
    surface.blit(text, (board.centerx - text.get_width() // 2, board.centery - text.get_height() // 2))


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
    "nadiya_idle_sprite",
    "nadiya_walk_cycle",
    "nadiya_eat_sprite",
    "mom_sprite",
    "neighbor_sprite",
    "cat_sprite",
    "plant_sprite",
    "sofa_sprite",
    "coffee_table_sprite",
    "tv_stand_sprite",
    "bookshelf_sprite",
    "bed_sprite",
    "wardrobe_sprite",
    "desk_sprite",
    "shower_sprite",
    "sink_sprite",
    "fridge_sprite",
    "stove_sprite",
    "counter_sprite",
    "classmate_variants",
    "draw_kitchen_background",
    "draw_school_background",
    "draw_school_exterior",
    "draw_school_hallway",
    "draw_school_lobby",
    "draw_living_room_background",
]
