"""Fade transition and summary screen between segments."""

from __future__ import annotations

from typing import List

import pygame

from game.config import COLORS
from game.scenes.base import Scene
from game.state import GameState, TimeSegment
from game.ui.fonts import PixelFont


class TransitionScene(Scene):
    def __init__(self, state: GameState, screen: pygame.Surface, *, summary: List[str], next_segment: TimeSegment, duration: float = 2.5) -> None:
        super().__init__(state)
        self.screen = screen
        self.font = PixelFont(base_size=14, scale=3, bold=True)
        self.small_font = PixelFont(base_size=12, scale=2)
        self.summary = summary or ["Another blur of a segment passes by."]
        self.next_segment = next_segment
        self.duration = duration
        self.timer = duration
        self.elapsed = 0.0
        self.fade_in = 0.5
        self.fade_out = 0.5
        self.min_display = 1.0
        self.alpha_surface = pygame.Surface(screen.get_size())
        self.alpha_surface.fill((0, 0, 0))
        self.alpha_surface.set_alpha(0)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if self.elapsed >= self.min_display:
                self.timer = 0

    def update(self, dt: float) -> None:
        self.elapsed += dt
        self.timer -= dt
        if self.timer <= 0:
            self.completed = True

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((14, 14, 20))
        title = self.font.render(f"Day {self.state.day} — {self.next_segment.name.title()} incoming", COLORS.text_light)
        surface.blit(title, (80, 120))
        for idx, line in enumerate(self.summary):
            summary_surface = self.small_font.render(f"• {line}", COLORS.text_light)
            surface.blit(summary_surface, (100, 180 + idx * 28))
        clock_surface = self.small_font.render(f"Clock: {self.state.formatted_clock()}", COLORS.accent_fries)
        surface.blit(clock_surface, (80, 140))

        fade_ratio = 0.0
        if self.elapsed < self.fade_in:
            fade_ratio = 1.0 - min(1.0, self.elapsed / self.fade_in)
        elif self.timer < self.fade_out:
            fade_ratio = 1.0 - max(0.0, self.timer / max(0.001, self.fade_out))
        alpha = int(fade_ratio * 200)
        self.alpha_surface.set_alpha(alpha)
        surface.blit(self.alpha_surface, (0, 0))


__all__ = ["TransitionScene"]
