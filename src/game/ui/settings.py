"""Pause/settings overlay displayed on top of active scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pygame

from game.ai.local_client import LocalAIClient
from game.config import COLORS
from game.state import GameState
from game.ui.fonts import PixelFont


@dataclass
class Option:
    label: str
    kind: str  # slider or toggle
    attr: str
    step: float = 0.1
    min_value: float = 0.0
    max_value: float = 1.0


class SettingsOverlay:
    def __init__(self, state: GameState, ai_client: LocalAIClient, screen: pygame.Surface) -> None:
        self.state = state
        self.ai_client = ai_client
        self.screen = screen
        self.active = False
        self.selection = 0
        self.title_font = PixelFont(base_size=14, scale=3, bold=True)
        self.option_font = PixelFont(base_size=12, scale=2)
        self.small_font = PixelFont(base_size=10, scale=2)
        self.options: List[Option] = [
            Option("Music Volume", "slider", "music_volume", step=0.1, min_value=0.0, max_value=1.0),
            Option("Effects Volume", "slider", "sfx_volume", step=0.1, min_value=0.0, max_value=1.0),
            Option("Text Speed", "slider", "text_speed", step=0.1, min_value=0.5, max_value=2.5),
            Option("Local AI Replies", "toggle", "ai_enabled"),
        ]

    def toggle(self) -> None:
        self.active = not self.active
        if not self.active:
            self.state.settings.clamp()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                self.toggle()
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.selection = (self.selection - 1) % len(self.options)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selection = (self.selection + 1) % len(self.options)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self._adjust(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self._adjust(1)

    def _adjust(self, direction: int) -> None:
        option = self.options[self.selection]
        if option.kind == "slider":
            current = getattr(self.state.settings, option.attr)
            current += option.step * direction
            current = max(option.min_value, min(option.max_value, current))
            setattr(self.state.settings, option.attr, round(current, 2))
            self.state.settings.clamp()
        elif option.kind == "toggle":
            if option.attr == "ai_enabled" and not self.ai_client.settings.enabled:
                self.state.settings.ai_enabled = False
            else:
                current = getattr(self.state.settings, option.attr)
                setattr(self.state.settings, option.attr, not current)

    def render(self) -> None:
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((10, 10, 14, 200))
        panel = pygame.Rect(0, 0, 560, 420)
        panel.center = self.screen.get_rect().center
        pygame.draw.rect(overlay, (38, 32, 46, 240), panel, border_radius=18)
        pygame.draw.rect(overlay, COLORS.accent_fries, panel, width=3, border_radius=18)

        title_surface = self.title_font.render("Settings", COLORS.text_light)
        overlay.blit(title_surface, (panel.centerx - title_surface.get_width() // 2, panel.top + 32))

        for idx, option in enumerate(self.options):
            value = getattr(self.state.settings, option.attr)
            label_surface = self.option_font.render(option.label, COLORS.text_light)
            if option.kind == "toggle":
                if option.attr == "ai_enabled" and not self.ai_client.settings.enabled:
                    value_text = "Off (server)"
                else:
                    value_text = "On" if value else "Off"
            else:
                value_text = f"{value:.2f}"
            value_surface = self.option_font.render(value_text, COLORS.accent_fries if idx == self.selection else COLORS.text_light)
            y = panel.top + 110 + idx * 70
            x_label = panel.left + 60
            overlay.blit(label_surface, (x_label, y))
            overlay.blit(value_surface, (panel.right - value_surface.get_width() - 80, y))
            if option.kind == "slider":
                track_rect = pygame.Rect(x_label, y + 42, panel.width - 140, 10)
                pygame.draw.rect(overlay, (54, 48, 66), track_rect, border_radius=5)
                denom = max(0.0001, option.max_value - option.min_value)
                ratio = (value - option.min_value) / denom
                knob_x = track_rect.left + int(track_rect.width * ratio)
                pygame.draw.circle(overlay, COLORS.accent_ui if idx == self.selection else COLORS.accent_fries, (knob_x, track_rect.centery), 8)

            if idx == self.selection:
                pygame.draw.rect(overlay, COLORS.accent_ui, (x_label - 16, y - 8, panel.width - 120, 70), 2, border_radius=12)

        hint_lines = [
            "Esc/Enter to close",
            "Arrows/WASD adjust",
            "AI replies require a local model server",
        ]
        for i, line in enumerate(hint_lines):
            text_surface = self.small_font.render(line, COLORS.text_light)
            overlay.blit(text_surface, (panel.left + 60, panel.bottom - 100 + i * 26))

        self.screen.blit(overlay, (0, 0))


__all__ = ["SettingsOverlay"]
