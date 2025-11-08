"""Evening chat controller with lightweight UI polish."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, List

import pygame

from game.balance import get_balance_section
from game.ai.local_client import AIRequest, LocalAIClient
from game.config import COLORS
from game.state import GameState
from game.ui.fonts import PixelFont


@dataclass
class ChatMessage:
    speaker: str
    text: str


class ChatController:
    def __init__(self, state: GameState, surface: pygame.Surface, ai_client: LocalAIClient) -> None:
        self.state = state
        self.surface = surface
        self.ai_client = ai_client
        self.title_font = PixelFont(base_size=14, scale=3, bold=True)
        self.font = PixelFont(base_size=12, scale=2)
        self.small_font = PixelFont(base_size=10, scale=2)
        self.messages: Deque[ChatMessage] = deque(maxlen=16)
        self.input_buffer: List[str] = []
        self.current_friend = "zara"
        self.pending_request: int | None = None
        self.completed = False
        self.timer = float(get_balance_section("segments").get("evening", {}).get("base_timer", 40))
        self.summary: List[str] = []
        self._evening_cfg = get_balance_section("segments").get("evening", {})
        self._event_cfg = get_balance_section("events")
        self._background = pygame.Surface(self.surface.get_size())
        self._background.fill((22, 20, 34))
        self._avatars = {
            "zara": self._build_avatar("Z", COLORS.accent_ui),
            "lukas": self._build_avatar("L", COLORS.accent_cool),
        }
        self.cursor_timer = 0.0
        self.cursor_visible = True
        self._bootstrap()

    def _bootstrap(self) -> None:
        self.messages.append(ChatMessage(self.current_friend.capitalize(), "Hey chaotic fry hero, how is life?"))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                text = "".join(self.input_buffer).strip()
                if text:
                    self._send_message(text)
                    self.input_buffer.clear()
            elif event.key == pygame.K_BACKSPACE:
                if self.input_buffer:
                    self.input_buffer.pop()
            elif event.key == pygame.K_TAB:
                self.current_friend = "lukas" if self.current_friend == "zara" else "zara"
                self.messages.append(ChatMessage("System", f"Switched chat to {self.current_friend.capitalize()}"))
            else:
                if event.unicode.isprintable():
                    self.input_buffer.append(event.unicode)

    def _send_message(self, text: str) -> None:
        self.messages.append(ChatMessage("Nadiya", text))
        self.state.apply_outcome(mood=1.0)
        persona = f"friend_{self.current_friend}"
        context = {
            "mood": "high" if self.state.stats.mood > 60 else "low" if self.state.stats.mood < 40 else "neutral",
            "day": str(self.state.day),
            "friend": self.current_friend,
        }
        if self.state.relationships.friends.get(self.current_friend, 50.0) < self._event_cfg.get("friend_ignore_threshold", 25):
            self.messages.append(ChatMessage(self.current_friend.capitalize(), "..."))
            self.summary.append(f"{self.current_friend.capitalize()} left you on read.")
            self.state.events.trigger("friend_ignores_you")
            penalty = float(self._evening_cfg.get("chat_mood_penalty", -2.0))
            self.state.apply_outcome(mood=penalty)
        else:
            request = AIRequest("Nadiya", persona, context, text)
            self.pending_request = self.ai_client.submit(request, callback=self._receive_response, allow_remote=self.state.settings.ai_enabled)

    def _receive_response(self, text: str) -> None:
        self.messages.append(ChatMessage(self.current_friend.capitalize(), text))
        self.state.relationships.adjust_friend(self.current_friend, 2.0)
        self.summary.append(f"{self.current_friend.capitalize()} boosted your mood with snark.")

    def update(self, dt: float) -> None:
        self.timer -= dt
        if self.timer <= 0:
            self.completed = True
            bonus = float(self._evening_cfg.get("chat_mood_bonus", 3.0))
            self.state.apply_outcome(mood=bonus)
            if not self.summary:
                self.summary.append("Quiet night online but you still exhaled.")
        self.cursor_timer += dt
        if self.cursor_timer >= 0.5:
            self.cursor_visible = not self.cursor_visible
            self.cursor_timer = 0.0

    def render(self) -> None:
        self.surface.blit(self._background, (0, 0))
        header = self.title_font.render(f"Chatting with {self.current_friend.capitalize()}", COLORS.text_light)
        self.surface.blit(header, (80, 60))
        panel = pygame.Surface((self.surface.get_width() - 160, 340), pygame.SRCALPHA)
        panel.fill((18, 16, 28, 220))
        panel_rect = panel.get_rect()
        panel_rect.topleft = (80, 110)
        y = panel.get_height() - 20
        for message in reversed(self.messages):
            avatar = self._avatars.get(message.speaker.lower())
            text_surface = self.font.render(message.text, COLORS.text_light if message.speaker != "System" else COLORS.accent_cool)
            bubble_width = text_surface.get_width() + 30
            bubble_height = text_surface.get_height() + 16
            if message.speaker == "Nadiya":
                bubble_rect = pygame.Rect(panel.get_width() - bubble_width - 20, y - bubble_height, bubble_width, bubble_height)
                color = (80, 52, 88, 220)
            else:
                bubble_rect = pygame.Rect(20, y - bubble_height, bubble_width, bubble_height)
                color = (42, 36, 58, 220)
            bubble = pygame.Surface(bubble_rect.size, pygame.SRCALPHA)
            bubble.fill(color)
            panel.blit(bubble, bubble_rect.topleft)
            panel.blit(text_surface, (bubble_rect.left + 14, bubble_rect.top + 6))
            if avatar and message.speaker != "Nadiya" and message.speaker != "System":
                panel.blit(avatar, (bubble_rect.left - avatar.get_width() - 8, bubble_rect.top))
            y -= bubble_height + 12
            if y < 40:
                break
        self.surface.blit(panel, panel_rect)

        input_panel = pygame.Surface((self.surface.get_width() - 160, 80), pygame.SRCALPHA)
        input_panel.fill((26, 22, 34, 220))
        input_rect = input_panel.get_rect()
        input_rect.topleft = (80, self.surface.get_height() - 130)
        self.surface.blit(input_panel, input_rect)
        typed_text = "".join(self.input_buffer)
        if self.cursor_visible:
            typed_text += "_"
        input_surface = self.font.render(typed_text or "Type something weird and supportive...", COLORS.accent_fries if typed_text else COLORS.text_light)
        self.surface.blit(input_surface, (input_rect.left + 20, input_rect.top + 24))
        helper_text = self.small_font.render("Enter to send • Backspace to delete • Tab to switch friend", COLORS.text_light)
        self.surface.blit(helper_text, (80, self.surface.get_height() - 60))
        if self.state.settings.ai_enabled and not self.ai_client.settings.enabled:
            warning = self.small_font.render("AI replies disabled (server offline)", COLORS.accent_ui)
            self.surface.blit(warning, (80, self.surface.get_height() - 90))

    def _build_avatar(self, label: str, color: tuple[int, int, int]) -> pygame.Surface:
        size = 40
        avatar = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(avatar, color, (size // 2, size // 2), size // 2)
        text = self.font.render(label, COLORS.text_light)
        rect = text.get_rect(center=(size // 2, size // 2))
        avatar.blit(text, rect)
        return avatar


__all__ = ["ChatController"]
