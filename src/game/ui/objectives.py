"""Simple objective overlay so players know what to do next."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List

import pygame

from game.config import COLORS
from game.ui.fonts import PixelFont


@dataclass
class ObjectivesOverlay:
    """Render a small task list that can be toggled with the H key."""

    screen: pygame.Surface
    font: PixelFont = field(default_factory=lambda: PixelFont(base_size=12, scale=2, bold=True))
    body_font: PixelFont = field(default_factory=lambda: PixelFont(base_size=11, scale=2))
    visible: bool = True
    _lines: List[str] = field(default_factory=list)
    _hint_timer: float = 8.0

    def set_lines(self, lines: Iterable[str]) -> None:
        """Replace the currently displayed objectives."""

        new_lines = [line.strip() for line in lines if line]
        if new_lines == self._lines:
            return
        self._lines = new_lines
        if self._lines:
            # Whenever we receive new objectives we make the overlay visible so
            # the player notices the change.
            self.visible = True
            self._hint_timer = 8.0

    def toggle(self) -> None:
        self.visible = not self.visible
        if self.visible and not self._lines:
            # Nothing to show, hide again to avoid rendering an empty panel.
            self.visible = False

    def update(self, dt: float) -> None:
        if self._hint_timer > 0:
            self._hint_timer -= dt

    def render(self) -> None:
        if not self.visible or not self._lines:
            return

        padding = 16
        max_width = self.screen.get_width() // 3
        line_surfaces: List[pygame.Surface] = []
        width = 0
        for idx, line in enumerate(self._lines, start=1):
            text = f"{idx}. {line}" if not line[0].isdigit() else line
            surface = self.body_font.render(text, COLORS.text_light)
            line_surfaces.append(surface)
            width = max(width, surface.get_width())

        title = self.font.render("What to do", COLORS.accent_ui)
        width = max(width, title.get_width())
        panel_width = min(max_width, width + padding * 2)
        panel_height = title.get_height() + padding * 2 + len(line_surfaces) * 28
        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(panel, (18, 14, 22, 220), panel.get_rect(), border_radius=12)
        pygame.draw.rect(panel, (0, 0, 0, 120), panel.get_rect(), border_radius=12, width=2)
        panel.blit(title, (padding // 2, padding // 2))

        y = title.get_height() + padding
        for surface in line_surfaces:
            panel.blit(surface, (padding // 2, y))
            y += 24

        self.screen.blit(panel, (24, self.screen.get_height() - panel_height - 24))

        if self._hint_timer > 0:
            hint_text = self.body_font.render("Press H to hide this panel", COLORS.text_dark)
            hint_bg = pygame.Surface((hint_text.get_width() + 20, hint_text.get_height() + 12), pygame.SRCALPHA)
            pygame.draw.rect(hint_bg, (12, 10, 18, 200), hint_bg.get_rect(), border_radius=8)
            hint_bg.blit(hint_text, (10, 6))
            self.screen.blit(hint_bg, (24, self.screen.get_height() - panel_height - hint_bg.get_height() - 36))


__all__ = ["ObjectivesOverlay"]

