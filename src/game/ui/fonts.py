"""Font helpers backed by ``pygame.freetype`` for crisp text rendering."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Tuple

import pygame
import pygame.freetype


@lru_cache(maxsize=8)
def _load_font(size: int, bold: bool) -> pygame.freetype.Font:
    """Return a cached ``pygame.freetype`` font instance."""

    font = pygame.freetype.SysFont("Segoe UI", size, bold=bold)
    if font is None:
        # ``SysFont`` can return ``None`` on some headless setups. Fall back to
        # the bundled default font in that situation.
        font = pygame.freetype.Font(None, size)
        font.strong = bold
    font.pad = True
    font.origin = True
    return font


@dataclass
class PixelFont:
    """Wrapper that renders high-quality text without manual scaling."""

    base_size: int = 16
    scale: int = 1
    bold: bool = False

    def __post_init__(self) -> None:
        # ``scale`` is preserved so existing configuration remains compatible,
        # but instead of blitting a tiny surface and upscaling it (which caused
        # blur), we request the appropriate point size directly from freetype.
        self.point_size = max(8, int(self.base_size * self.scale))
        self._font = _load_font(self.point_size, self.bold)

    def render(self, text: str, color: tuple[int, int, int]) -> pygame.Surface:
        surface, _ = self._font.render(text, color)
        return surface.convert_alpha()

    def size(self, text: str) -> Tuple[int, int]:
        rect = self._font.get_rect(text)
        return rect.width, rect.height


__all__ = ["PixelFont"]
