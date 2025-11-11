"""Sleep transition scene that advances to next day."""

from __future__ import annotations

import random

import pygame

from game.balance import get_balance_section
from game.config import COLORS
from game.scenes.base import Scene
from game.state import GameState

DREAMS = [
    "You dream about fries forming a choir, singing in German.",
    "The school hallway becomes a river and you float past vocabulary words.",
    "Mom builds a spaceship out of cooking pots and invites you to steer.",
]


class SleepScene(Scene):
    def __init__(self, state: GameState, screen: pygame.Surface) -> None:
        super().__init__(state)
        self.screen = screen
        self.font = pygame.font.Font(None, 36)
        self.timer = 4.5
        self.dream_text = random.choice(DREAMS)
        self.state.flags.seen_dreams.append(self.dream_text)
        self.summary: list[str] = []
        self._sleep_cfg = get_balance_section("sleep")
        self._prepare_rest()

    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    def update(self, dt: float) -> None:
        self.timer -= dt
        if self.timer <= 0:
            self.state.advance_segment()
            self.completed = True

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((12, 12, 20))
        text_surface = self.font.render("Sleeping...", True, COLORS.text_light)
        dream_surface = self.font.render(self.dream_text, True, COLORS.accent_fries)
        surface.blit(text_surface, (surface.get_width() // 2 - text_surface.get_width() // 2, 200))
        surface.blit(dream_surface, (80, 280))

    def get_objectives(self) -> list[str]:
        return [
            "Resting — nothing to do but wait a few seconds.",
            "Tomorrow will start at dawn with a fresh checklist.",
        ]

    def _prepare_rest(self) -> None:
        restore = float(self._sleep_cfg.get("base_restore", 30))
        if self.state.stats.energy < 20:
            self.summary.append("Body finally collapses into bed. Energy emergency.")
        else:
            self.summary.append("Wind down ritual complete; sleep creeps in gently.")
        if random.random() < min(0.6, restore / 100):
            self.state.events.trigger("dream_fragment")
            self.summary.append("Dream fragments cling to the morning edges.")


__all__ = ["SleepScene"]
