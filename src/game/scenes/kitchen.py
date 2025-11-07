"""Afternoon kitchen segment focusing on the fry minigame."""

from __future__ import annotations

import pygame

from game.minigames.fry_minigame import FryMinigameController
from game.scenes.base import Scene
from game.state import GameState


class KitchenScene(Scene):
    def __init__(self, state: GameState, screen: pygame.Surface) -> None:
        super().__init__(state)
        self.screen = screen
        self.minigame = FryMinigameController(state, screen)
        self.summary: list[str] = []

    def handle_event(self, event: pygame.event.Event) -> None:
        self.minigame.handle_event(event)

    def update(self, dt: float) -> None:
        self.minigame.update(dt)
        if self.minigame.completed:
            self.completed = True
            if not self.summary:
                self.summary.extend(self.minigame.summary)

    def render(self, surface: pygame.Surface) -> None:
        self.minigame.render()


__all__ = ["KitchenScene"]
