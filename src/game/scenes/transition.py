"""Fade transition and summary screen between segments."""

from __future__ import annotations

from typing import List

import pygame

from game.config import COLORS
from game.scenes.base import Scene
from game.state import GameState, TimeSegment


class TransitionScene(Scene):
    def __init__(self, state: GameState, screen: pygame.Surface, *, summary: List[str], next_segment: TimeSegment, duration: float = 2.5) -> None:
        super().__init__(state)
        self.screen = screen
        self.font = pygame.font.Font(None, 32)
        self.small_font = pygame.font.Font(None, 24)
        self.summary = summary or ["Another blur of a segment passes by."]
        self.next_segment = next_segment
        self.duration = duration
        self.timer = duration
        self.alpha_surface = pygame.Surface(screen.get_size())
        self.alpha_surface.fill((0, 0, 0))
        self.alpha_surface.set_alpha(0)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self.timer = 0

    def update(self, dt: float) -> None:
        self.timer -= dt
        if self.timer <= 0:
            self.completed = True

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((14, 14, 20))
        title = self.font.render(f"Day {self.state.day} — {self.next_segment.name.title()} incoming", True, COLORS.text_light)
        surface.blit(title, (80, 120))
        for idx, line in enumerate(self.summary):
            summary_surface = self.small_font.render(f"• {line}", True, COLORS.text_light)
            surface.blit(summary_surface, (100, 180 + idx * 28))
        progress = max(0.0, self.timer / self.duration)
        alpha = int((1.0 - progress) * 180)
        self.alpha_surface.set_alpha(alpha)
        surface.blit(self.alpha_surface, (0, 0))


__all__ = ["TransitionScene"]
