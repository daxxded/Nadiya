"""Reusable overlay for in-world conversations and choices."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

import pygame

from game.ai.local_client import AIRequest, LocalAIClient
from game.config import COLORS
from game.state import GameState
from game.ui.fonts import PixelFont


@dataclass
class DialogueChoice:
    label: str
    callback: Callable[[], None]


class DialogueOverlay:
    """Small chat window that supports canned lines, choices, and AI typing."""

    def __init__(self, state: GameState, ai_client: LocalAIClient, screen: pygame.Surface) -> None:
        self.state = state
        self.ai_client = ai_client
        self.screen = screen
        self.font = PixelFont(base_size=11, scale=2)
        self.small_font = PixelFont(base_size=9, scale=2)
        self.title_font = PixelFont(base_size=13, scale=3, bold=True)
        self.messages: List[str] = []
        self.choices: List[DialogueChoice] = []
        self.choice_index = 0
        self.input_buffer: List[str] = []
        self.cursor_timer = 0.0
        self.cursor_visible = True
        self.active = False
        self.mode: str = "idle"
        self.speaker = ""
        self.persona: Optional[str] = None
        self.pending_request: Optional[int] = None
        self._context_builder: Optional[Callable[[], dict[str, str]]] = None
        self.summary: List[str] = []

    def open_info(self, speaker: str, lines: List[str]) -> None:
        self._reset()
        self.active = True
        self.mode = "info"
        self.speaker = speaker
        self.messages.extend([f"{speaker}: {line}" for line in lines])

    def open_choices(self, speaker: str, lines: List[str], choices: List[DialogueChoice]) -> None:
        self._reset()
        self.active = True
        self.mode = "choice"
        self.speaker = speaker
        self.messages.extend([f"{speaker}: {line}" for line in lines])
        self.choices = list(choices)
        self.choice_index = 0

    def open_ai(self, speaker: str, persona: str, *, context_builder: Callable[[], dict[str, str]]) -> None:
        self._reset()
        self.active = True
        self.mode = "ai"
        self.speaker = speaker
        self.persona = persona
        self._context_builder = context_builder
        self.messages.append(f"{speaker}: Hey, what's up?")

    def close(self) -> None:
        self.active = False
        self.mode = "idle"
        self.persona = None
        self.choices.clear()
        self.input_buffer.clear()
        self.pending_request = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.active:
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_q, pygame.K_x, pygame.K_TAB):
                self.close()
                return
            if self.mode == "info":
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.close()
                return
            if self.mode == "choice":
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    self.choice_index = (self.choice_index + 1) % max(1, len(self.choices))
                elif event.key in (pygame.K_UP, pygame.K_w):
                    self.choice_index = (self.choice_index - 1) % max(1, len(self.choices))
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE) and self.choices:
                    choice = self.choices[self.choice_index]
                    choice.callback()
                    self.summary.append(f"Chose: {choice.label}")
                    self.close()
                return
            if self.mode == "ai":
                if event.key == pygame.K_RETURN:
                    text = "".join(self.input_buffer).strip()
                    if text and not self.pending_request:
                        self._send_ai(text)
                elif event.key == pygame.K_BACKSPACE:
                    if self.input_buffer:
                        self.input_buffer.pop()
                else:
                    if event.unicode and event.unicode.isprintable():
                        self.input_buffer.append(event.unicode)

    def update(self, dt: float) -> None:
        if not self.active:
            return
        self.cursor_timer += dt
        if self.cursor_timer >= 0.5:
            self.cursor_visible = not self.cursor_visible
            self.cursor_timer = 0.0

    def render(self) -> None:
        if not self.active:
            return
        overlay = pygame.Surface((self.screen.get_width(), 260), pygame.SRCALPHA)
        overlay.fill((18, 16, 24, 220))
        rect = overlay.get_rect()
        rect.midbottom = (self.screen.get_width() // 2, self.screen.get_height() - 20)
        self.screen.blit(overlay, rect)

        title = self.title_font.render(self.speaker, COLORS.accent_ui)
        self.screen.blit(title, (rect.left + 20, rect.top + 18))

        y = rect.top + 64
        for line in self.messages[-5:]:
            text_surface = self.font.render(line, COLORS.text_light)
            self.screen.blit(text_surface, (rect.left + 20, y))
            y += text_surface.get_height() + 6

        if self.mode == "choice":
            choice_y = rect.bottom - 86
            for idx, choice in enumerate(self.choices):
                label = choice.label
                color = COLORS.accent_fries if idx == self.choice_index else COLORS.text_light
                label_surface = self.font.render(label, color)
                self.screen.blit(label_surface, (rect.left + 40, choice_y))
                choice_y += label_surface.get_height() + 6
            hint = self.small_font.render("↑/↓ to choose • Enter to confirm", COLORS.text_light)
            self.screen.blit(hint, (rect.left + 20, rect.bottom - 40))
        elif self.mode == "ai":
            input_text = "".join(self.input_buffer)
            if self.cursor_visible:
                input_text += "_"
            input_surface = self.font.render(input_text or "Type and press Enter", COLORS.text_light)
            self.screen.blit(input_surface, (rect.left + 20, rect.bottom - 80))
            if self.pending_request:
                waiting = self.small_font.render("Waiting for reply...", COLORS.accent_cool)
                self.screen.blit(waiting, (rect.left + 20, rect.bottom - 48))
        else:
            hint = self.small_font.render("Enter to close", COLORS.text_light)
            self.screen.blit(hint, (rect.left + 20, rect.bottom - 40))

    def consume_summary(self) -> List[str]:
        lines = list(dict.fromkeys(self.summary))
        self.summary.clear()
        return lines

    def _reset(self) -> None:
        self.messages.clear()
        self.choices.clear()
        self.choice_index = 0
        self.input_buffer.clear()
        self.pending_request = None
        self.summary.clear()

    def _send_ai(self, text: str) -> None:
        self.messages.append(f"You: {text}")
        if not self.persona or not self._context_builder:
            self.messages.append(f"{self.speaker}: I'll think about it later.")
            return
        context = self._context_builder()
        request = AIRequest("Nadiya", self.persona, context, text)
        self.pending_request = self.ai_client.submit(
            request,
            callback=self._receive_ai,
            allow_remote=self.state.settings.ai_enabled,
        )

    def _receive_ai(self, text: str) -> None:
        self.pending_request = None
        self.messages.append(f"{self.speaker}: {text}")
        self.summary.append(f"Chatted with {self.speaker}.")


__all__ = ["DialogueOverlay", "DialogueChoice"]
