"""Legacy wrapper scene that opens the phone overlay directly."""

from __future__ import annotations

import pygame

from game.ai.local_client import LocalAIClient
from game.scenes.base import Scene
from game.state import GameState
from game.ui.phone import PhoneOverlay


class ChatScene(Scene):
    """Fallback scene to open the phone overlay outside of home exploration."""

    def __init__(self, state: GameState, screen: pygame.Surface, ai_client: LocalAIClient) -> None:
        super().__init__(state)
        self.screen = screen
        self.phone = PhoneOverlay(state, ai_client, screen)
        self.summary: list[str] = []

    def on_enter(self) -> None:
        self.phone.open()
        self.phone.active_app = "discord"

    def handle_event(self, event: pygame.event.Event) -> None:
        self.phone.handle_event(event)

    def update(self, dt: float) -> None:
        self.phone.update(dt)
        if not self.phone.active and self.phone.completed:
            summary = self.phone.consume_summary()
            if summary:
                self.summary.extend(summary)
            if not self.summary:
                self.summary.append("Scrolled Discord for a while.")
            self.completed = True

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((14, 12, 20))
        self.phone.render()


__all__ = ["ChatScene"]
