"""Evening chat scene connecting to the chat controller."""

from __future__ import annotations

import pygame

from game.ai.local_client import LocalAIClient
from game.minigames.chat import ChatController
from game.scenes.base import Scene
from game.state import GameState


class ChatScene(Scene):
    def __init__(self, state: GameState, screen: pygame.Surface, ai_client: LocalAIClient) -> None:
        super().__init__(state)
        self.screen = screen
        self.controller = ChatController(state, screen, ai_client)
        self.summary: list[str] = []

    def handle_event(self, event: pygame.event.Event) -> None:
        self.controller.handle_event(event)

    def update(self, dt: float) -> None:
        self.controller.update(dt)
        if self.controller.completed:
            self.completed = True
            if not self.summary:
                self.summary.extend(self.controller.summary)

    def render(self, surface: pygame.Surface) -> None:
        self.controller.render()


__all__ = ["ChatScene"]
