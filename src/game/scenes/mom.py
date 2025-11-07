"""Night scene with Nadiya's mom."""

from __future__ import annotations

import random

import pygame

from game.balance import get_balance_section
from game.ai.local_client import AIRequest, LocalAIClient
from game.config import COLORS
from game.dialogue import DialogueManager
from game.scenes.base import Scene
from game.state import GameState


class MomScene(Scene):
    def __init__(self, state: GameState, ai_client: LocalAIClient, screen: pygame.Surface) -> None:
        super().__init__(state)
        self.ai_client = ai_client
        self.screen = screen
        self.font = pygame.font.Font(None, 32)
        self.small_font = pygame.font.Font(None, 26)
        self.dialogue: list[str] = []
        self.choice_index = 0
        self.waiting_for_ai = False
        self.summary: list[str] = []
        self._dialogue_manager = DialogueManager()
        self._active_choices: list[tuple[str, str]] = []
        self._mode = "neutral"
        self._events_cfg = get_balance_section("events")

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
        surface.fill((28, 26, 32))
        y = 100
        for line in self.dialogue[-6:]:
            text_surface = self.font.render(line, True, COLORS.text_light)
            surface.blit(text_surface, (80, y))
            y += 40

        if not self.completed:
            for idx, choice in enumerate(self._active_choices):
                _, label = choice
                color = COLORS.accent_ui if idx == self.choice_index else COLORS.text_light
                choice_surface = self.font.render(label, True, color)
                surface.blit(choice_surface, (120, 420 + idx * 36))
        if self.waiting_for_ai:
            typing_surface = self.small_font.render("Mom is thinking...", True, COLORS.accent_cool)
            surface.blit(typing_surface, (120, 520))

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
        self.ai_client.submit(request, callback=self._on_ai_response)

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
