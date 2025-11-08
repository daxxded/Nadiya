"""Helpers for consistent pixel-style fonts across the prototype."""

from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass
class PixelFont:
    """Tiny wrapper that renders crisp, scaled bitmap-like text."""

    base_size: int = 12
    scale: int = 2
    bold: bool = False

    def __post_init__(self) -> None:
        self._font = pygame.font.Font(None, self.base_size)
        self._font.set_bold(self.bold)

    def render(self, text: str, color: tuple[int, int, int]) -> pygame.Surface:
        surface = self._font.render(text, True, color)
        if self.scale != 1:
            surface = pygame.transform.scale(surface, (surface.get_width() * self.scale, surface.get_height() * self.scale))
        return surface

    def size(self, text: str) -> tuple[int, int]:
        width, height = self._font.size(text)
        return width * self.scale, height * self.scale


__all__ = ["PixelFont"]
