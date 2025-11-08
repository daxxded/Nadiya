"""HUD rendering for stats and time of day."""

from __future__ import annotations

import pygame

from game.config import COLORS
from game.state import GameState, TimeSegment
from game.ui.fonts import PixelFont


class StatusBar:
    def __init__(self, label: str, color: tuple[int, int, int], max_value: float = 100.0) -> None:
        self.label = label
        self.color = color
        self.max_value = max_value

    def render(self, surface: pygame.Surface, font: PixelFont, value: float, position: tuple[int, int]) -> None:
        x, y = position
        max_width = 220
        bar_height = 24
        ratio = max(0.0, min(1.0, value / self.max_value))
        pygame.draw.rect(surface, (0, 0, 0, 140), (x - 4, y - 4, max_width + 8, bar_height + 8), border_radius=6)
        pygame.draw.rect(surface, COLORS.warm_neutral, (x, y, max_width, bar_height), border_radius=4)
        pygame.draw.rect(surface, self.color, (x, y, int(max_width * ratio), bar_height), border_radius=4)
        label_surface = font.render(f"{self.label}: {int(value)}", COLORS.text_dark)
        surface.blit(label_surface, (x + 6, y + 4))


class HUD:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.font = PixelFont(base_size=12, scale=2)
        self.big_font = PixelFont(base_size=14, scale=3, bold=True)
        self.clock_font = PixelFont(base_size=12, scale=2)
        self.mood_bar = StatusBar("Mood", COLORS.accent_ui)
        self.hunger_bar = StatusBar("Hunger", COLORS.accent_fries)
        self.energy_bar = StatusBar("Energy", COLORS.accent_cool)

    def render(self, state: GameState) -> None:
        self.mood_bar.render(self.screen, self.font, state.stats.mood, (24, 24))
        self.hunger_bar.render(self.screen, self.font, state.stats.hunger, (24, 64))
        self.energy_bar.render(self.screen, self.font, state.stats.energy, (24, 104))

        segment_text = self.big_font.render(f"{segment_label(state.segment)}", COLORS.text_light)
        day_text = self.big_font.render(f"Day {state.day}", COLORS.text_light)
        segment_bg = pygame.Surface((segment_text.get_width() + 24, segment_text.get_height() + 16), pygame.SRCALPHA)
        segment_bg.fill((*COLORS.warm_dark, 200))
        segment_bg.blit(segment_text, (12, 8))
        self.screen.blit(segment_bg, (self.screen.get_width() // 2 - segment_bg.get_width() // 2, 24))

        day_bg = pygame.Surface((day_text.get_width() + 16, day_text.get_height() + 12), pygame.SRCALPHA)
        day_bg.fill((*COLORS.warm_dark, 200))
        day_bg.blit(day_text, (8, 6))
        self.screen.blit(day_bg, (self.screen.get_width() - day_bg.get_width() - 24, 24))

        self._render_clock(state)

    def _render_clock(self, state: GameState) -> None:
        time_text = self.clock_font.render(state.formatted_clock(), COLORS.text_light)
        clock_bg = pygame.Surface((time_text.get_width() + 20, time_text.get_height() + 14), pygame.SRCALPHA)
        clock_bg.fill((*COLORS.warm_dark, 210))
        clock_bg.blit(time_text, (10, 7))
        self.screen.blit(clock_bg, (self.screen.get_width() - clock_bg.get_width() - 24, 80))

        progress_width = 180
        progress_height = 10
        progress_rect = pygame.Rect(self.screen.get_width() - progress_width - 24, 80 + clock_bg.get_height() + 12, progress_width, progress_height)
        pygame.draw.rect(self.screen, (58, 48, 46), progress_rect, border_radius=6)
        if state.segment_duration > 0:
            ratio = max(0.0, min(1.0, state.segment_time / state.segment_duration))
        else:
            ratio = 0.0
        fill_rect = pygame.Rect(progress_rect.left, progress_rect.top, int(progress_rect.width * ratio), progress_rect.height)
        pygame.draw.rect(self.screen, COLORS.accent_fries, fill_rect, border_radius=6)


def segment_label(segment: TimeSegment) -> str:
    return {
        TimeSegment.MORNING: "Morning - School",
        TimeSegment.AFTERNOON: "Afternoon - Kitchen",
        TimeSegment.EVENING: "Evening - Friends",
        TimeSegment.NIGHT: "Night - Mom"
    }[segment]


__all__ = ["HUD"]
