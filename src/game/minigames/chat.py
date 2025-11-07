"""Text chat interface with AI stubs."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, List

import pygame

from game.balance import get_balance_section
from game.ai.local_client import AIRequest, LocalAIClient
from game.config import COLORS
from game.state import GameState


@dataclass
class ChatMessage:
    speaker: str
    text: str


class ChatController:
    def __init__(self, state: GameState, surface: pygame.Surface, ai_client: LocalAIClient) -> None:
        self.state = state
        self.surface = surface
        self.ai_client = ai_client
        self.font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 24)
        self.messages: Deque[ChatMessage] = deque(maxlen=12)
        self.input_buffer: List[str] = []
        self.current_friend = "zara"
        self.pending_request: int | None = None
        self.completed = False
        self.timer = 60.0
        self.summary: List[str] = []
        self._evening_cfg = get_balance_section("segments").get("evening", {})
        self._event_cfg = get_balance_section("events")
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
            self.pending_request = self.ai_client.submit(request, callback=self._receive_response)

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

    def render(self) -> None:
        self.surface.fill((18, 18, 26))
        y = 80
        for message in self.messages:
            color = COLORS.accent_ui if message.speaker == "Nadiya" else COLORS.text_light
            render = self.font.render(f"{message.speaker}: {message.text}", True, color)
            self.surface.blit(render, (80, y))
            y += 32

        input_text = "".join(self.input_buffer)
        input_surface = self.font.render(f"> {input_text}", True, COLORS.accent_fries)
        self.surface.blit(input_surface, (80, self.surface.get_height() - 120))

        helper_text = self.small_font.render("Enter to send • Backspace to delete • Tab to switch friend", True, COLORS.text_light)
        self.surface.blit(helper_text, (80, self.surface.get_height() - 80))


__all__ = ["ChatController"]
