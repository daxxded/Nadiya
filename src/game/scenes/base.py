"""Base scene logic for the Nadiya Simulator prototype."""

from __future__ import annotations

import pygame

from game.state import GameState


class Scene:
    """Abstract base for interactive scenes."""

    def __init__(self, state: GameState) -> None:
        self.state = state
        self.completed = False

    def handle_event(self, event: pygame.event.Event) -> None:
        raise NotImplementedError

    def update(self, dt: float) -> None:
        raise NotImplementedError

    def render(self, surface: pygame.Surface) -> None:
        raise NotImplementedError

    def on_enter(self) -> None:
        """Called when the scene becomes active."""

    def on_exit(self) -> None:
        """Called before the scene transitions out."""

    def get_summary(self) -> list[str]:
        """Return summary bullet lines for the transition screen."""

        lines = [str(line) for line in getattr(self, "summary", []) if line]
        if not lines:
            lines = [self.__class__.__name__.replace("Scene", "") + " wrapped without drama."]
        return lines


__all__ = ["Scene"]
