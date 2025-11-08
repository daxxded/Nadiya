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
        backdrop = pygame.Surface((max_width + 12, bar_height + 12), pygame.SRCALPHA)
        pygame.draw.rect(backdrop, (12, 10, 16, 160), backdrop.get_rect(), border_radius=6)
        surface.blit(backdrop, (x - 6, y - 6))
        pygame.draw.rect(surface, COLORS.warm_neutral, (x, y, max_width, bar_height), border_radius=6)
        pygame.draw.rect(surface, self.color, (x, y, int(max_width * ratio), bar_height), border_radius=4)
        label_text = f"{self.label}: {int(value)}"
        label_shadow = font.render(label_text, COLORS.warm_dark)
        label_surface = font.render(label_text, COLORS.text_dark)
        surface.blit(label_shadow, (x + 8, y + 6))
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

        segment_label_text = segment_label(state.segment)
        segment_text = self.big_font.render(segment_label_text, COLORS.text_light)
        header_width = max(segment_text.get_width() + 80, 360)
        header_rect = pygame.Rect(0, 0, header_width, segment_text.get_height() + 24)
        header_rect.centerx = self.screen.get_width() // 2
        header_rect.top = 18
        header_surface = pygame.Surface(header_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(header_surface, (24, 18, 30, 220), header_surface.get_rect(), border_radius=14)
        shadow = pygame.Surface(header_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 120), shadow.get_rect(), border_radius=14)
        self.screen.blit(shadow, (header_rect.left + 2, header_rect.top + 2))
        header_surface.blit(segment_text, (header_surface.get_width() // 2 - segment_text.get_width() // 2, 10))
        self.screen.blit(header_surface, header_rect.topleft)

        day_text = self.big_font.render(f"Day {state.day}", COLORS.text_light)
        day_bg = pygame.Surface((day_text.get_width() + 22, day_text.get_height() + 14), pygame.SRCALPHA)
        pygame.draw.rect(day_bg, (26, 20, 32, 220), day_bg.get_rect(), border_radius=10)
        shadow = pygame.Surface(day_bg.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 120), shadow.get_rect(), border_radius=10)
        pos = (self.screen.get_width() - day_bg.get_width() - 28, 26)
        self.screen.blit(shadow, (pos[0] + 2, pos[1] + 2))
        day_bg.blit(day_text, (10, 6))
        self.screen.blit(day_bg, pos)

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
        TimeSegment.AFTERNOON: "Afternoon - Home",
        TimeSegment.EVENING: "Evening - Phone",
        TimeSegment.NIGHT: "Night - Mom"
    }[segment]


__all__ = ["HUD"]
