"""Ten-second tram interstitial scene."""

from __future__ import annotations

import pygame

from game.config import COLORS
from game.scenes.base import Scene
from game.state import GameState, TimeSegment
from game.ui.fonts import PixelFont


class TramScene(Scene):
    def __init__(
        self,
        state: GameState,
        screen: pygame.Surface,
        *,
        direction: str,
        target_segment: TimeSegment,
    ) -> None:
        super().__init__(state)
        self.screen = screen
        self.direction = direction
        self.target_segment = target_segment
        self.font = PixelFont(base_size=12, scale=2)
        self.big_font = PixelFont(base_size=16, scale=3, bold=True)
        self.duration = 10.0
        self.elapsed = 0.0
        self.summary = [f"Rode the tram {direction}."]

    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    def update(self, dt: float) -> None:
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.completed = True

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((32, 28, 44))
        rail_color = (68, 60, 92)
        for i in range(0, surface.get_height(), 40):
            pygame.draw.rect(surface, rail_color, (0, i + (int(self.elapsed * 60) % 40), surface.get_width(), 8))
        tram_rect = pygame.Rect(120, surface.get_height() // 2 - 70, surface.get_width() - 240, 140)
        pygame.draw.rect(surface, (96, 88, 140), tram_rect, border_radius=24)
        window_rect = tram_rect.inflate(-40, -40)
        pygame.draw.rect(surface, (166, 186, 210), window_rect, border_radius=18)
        label = self.big_font.render("Tram", COLORS.text_light)
        surface.blit(label, (tram_rect.centerx - label.get_width() // 2, tram_rect.top + 16))
        sub = self.font.render(f"Heading {self.direction}", COLORS.accent_ui)
        surface.blit(sub, (tram_rect.centerx - sub.get_width() // 2, tram_rect.bottom - 46))


__all__ = ["TramScene"]
