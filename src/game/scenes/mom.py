"""Night segment with mom featuring optional AI dialogue."""

from __future__ import annotations

import random

import pygame

from game.balance import get_balance_section
from game.ai.local_client import AIRequest, LocalAIClient
from game.config import COLORS
from game.dialogue import DialogueManager
from game.scenes.base import Scene
from game.state import GameState
from game.ui.fonts import PixelFont
from game.ui.pixel_art import draw_living_room_background, mom_sprite, nadiya_sprite


class MomScene(Scene):
    def __init__(self, state: GameState, ai_client: LocalAIClient, screen: pygame.Surface) -> None:
        super().__init__(state)
        self.ai_client = ai_client
        self.screen = screen
        self.font = PixelFont(base_size=12, scale=2)
        self.big_font = PixelFont(base_size=14, scale=3, bold=True)
        self.dialogue: list[str] = []
        self.choice_index = 0
        self.waiting_for_ai = False
        self.summary: list[str] = []
        self._dialogue_manager = DialogueManager()
        self._active_choices: list[tuple[str, str]] = []
        self._mode = "neutral"
        self._events_cfg = get_balance_section("events")
        self.background = pygame.Surface(self.screen.get_size())
        draw_living_room_background(self.background)
        self.mom_sprite = mom_sprite()
        self.nadiya_sprite = nadiya_sprite()
        self.status_message = ""

    def on_enter(self) -> None:
        self._mode = self._decide_mode()
        preferred_nodes = ["drunk", "default"]
        if self._mode != "drunk":
            preferred_nodes.reverse()
        node = self._dialogue_manager.start("mom", preferred_nodes, self.state.events)
        if node:
            for line in node.lines:
                formatted = line.replace("{{mood_descriptor}}", self.state.mood_descriptor())
                self.dialogue.append(f"Narration: {formatted}")
            self._active_choices = [(choice.id, choice.text) for choice in node.choices] or [("wrap", "Say goodnight")]
        else:
            self._active_choices = [("wrap", "Say goodnight")]
        self.dialogue.append("Mom: Hey kiddo, you're up late again.")
        self._trigger_ai()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.choice_index = (self.choice_index + 1) % max(1, len(self._active_choices))
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.choice_index = (self.choice_index - 1) % max(1, len(self._active_choices))
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._select_choice()
            elif event.key == pygame.K_ESCAPE:
                self.completed = True

    def update(self, dt: float) -> None:
        pass

    def render(self, surface: pygame.Surface) -> None:
        surface.blit(self.background, (0, 0))
        self._draw_characters(surface)
        self._draw_dialogue(surface)
        self._draw_choices(surface)
        if self.waiting_for_ai:
            typing_surface = self.font.render("Mom is thinking...", COLORS.accent_cool)
            surface.blit(typing_surface, (120, 520))
        if self.state.settings.ai_enabled and not self.ai_client.settings.enabled:
            warning = self.font.render("AI server offline — using canned lines", COLORS.accent_ui)
            surface.blit(warning, (80, 560))

    def _draw_characters(self, surface: pygame.Surface) -> None:
        mom_rect = self.mom_sprite.get_rect()
        mom_rect.bottomleft = (120, surface.get_height() - 80)
        surface.blit(self.mom_sprite, mom_rect)
        nadiya_rect = self.nadiya_sprite.get_rect()
        nadiya_rect.bottomright = (surface.get_width() - 120, surface.get_height() - 60)
        surface.blit(self.nadiya_sprite, nadiya_rect)

    def _draw_dialogue(self, surface: pygame.Surface) -> None:
        panel = pygame.Surface((surface.get_width() - 160, 220), pygame.SRCALPHA)
        panel.fill((18, 14, 20, 220))
        panel_rect = panel.get_rect()
        panel_rect.topleft = (80, 100)
        surface.blit(panel, panel_rect)
        lines = self.dialogue[-6:]
        y = panel_rect.top + 20
        for line in lines:
            speaker, _, text = line.partition(":")
            speaker_surface = self.font.render(f"{speaker.strip()}:", COLORS.accent_fries)
            surface.blit(speaker_surface, (panel_rect.left + 20, y))
            text_surface = self.font.render(text.strip(), COLORS.text_light)
            surface.blit(text_surface, (panel_rect.left + 150, y))
            y += 32

    def _draw_choices(self, surface: pygame.Surface) -> None:
        if self.completed or not self._active_choices:
            return
        for idx, choice in enumerate(self._active_choices):
            _, label = choice
            y = 360 + idx * 44
            rect = pygame.Rect(0, 0, surface.get_width() - 240, 36)
            rect.center = (surface.get_width() // 2, y)
            bg_color = (60, 42, 58, 220) if idx == self.choice_index else (36, 28, 34, 200)
            panel = pygame.Surface(rect.size, pygame.SRCALPHA)
            panel.fill(bg_color)
            surface.blit(panel, rect)
            text_color = COLORS.accent_ui if idx == self.choice_index else COLORS.text_light
            label_surface = self.font.render(label, text_color)
            surface.blit(label_surface, (rect.left + 20, rect.top + 6))

    def _trigger_ai(self) -> None:
        if self.waiting_for_ai:
            return
        mode = self._mode
        self.state.flags.mom_modes[self.state.day] = mode
        context = {
            "day": str(self.state.day),
            "mood": "high" if self.state.stats.mood > 65 else "low" if self.state.stats.mood < 35 else "neutral",
            mode: "true",
            "relationship": str(int(self.state.relationships.mom)),
        }
        request = AIRequest("Nadiya", "mom", context, "Mom starts the conversation")
        self.waiting_for_ai = True
        self.ai_client.submit(request, callback=self._on_ai_response, allow_remote=self.state.settings.ai_enabled)

    def _on_ai_response(self, text: str) -> None:
        self.waiting_for_ai = False
        self.dialogue.append(f"Mom: {text}")
        if self._mode == "drunk":
            self.summary.append("Mom overshared stories with a soft slur.")
        elif self._mode == "tired":
            self.summary.append("She looked exhausted but tried to be present.")
        else:
            self.summary.append("Calm night chat with mom.")
        if not self._active_choices:
            self.completed = True

    def _select_choice(self) -> None:
        if not self._active_choices:
            self.completed = True
            return
        choice_id, choice_label = self._active_choices[self.choice_index]
        self.dialogue.append(f"Nadiya: {choice_label}")
        if choice_id == "share_fries":
            self.state.apply_outcome(mood=4.0)
            self.summary.append("Shared fry heroics with mom; laughter ensued.")
        elif choice_id == "ask_her":
            self.state.relationships.adjust_mom(3.0)
            self.summary.append("Asked about her night; she softened visibly.")
        elif choice_id == "listen":
            self.state.relationships.adjust_mom(4.0)
            self.summary.append("Let mom monologue. She needed it.")
        elif choice_id == "redirect":
            self.state.apply_outcome(mood=-2.0)
            self.summary.append("Deflected the heavy talk; tension lingers.")
        else:
            self.summary.append("Called it a night early.")
        if not self.waiting_for_ai:
            self.completed = True

    def _decide_mode(self) -> str:
        if self.state.stats.mood < 30:
            return "tired"
        threshold = float(self._events_cfg.get("mom_drunk_threshold", 70))
        if self.state.relationships.mom >= threshold and random.random() < 0.4:
            self.state.events.trigger("mom_drunk_night")
            return "drunk"
        return random.choice(["neutral", "tired"])


__all__ = ["MomScene"]
