"""Micro German quiz aligned with the design spec."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Sequence

import pygame

from game.balance import get_balance_section
from game.config import COLORS
from game.state import GameState


@dataclass
class Question:
    prompt: str
    options: Sequence[str]
    correct_index: int


QUESTIONS: List[Question] = [
    Question("Choose the correct article: ___ Kaffee", ["Der", "Die", "Das"], 0),
    Question("Wie sagt man 'tired' auf Deutsch?", ["müde", "kalt", "heiß"], 0),
    Question("Welches Wort passt? Ich ___ Pommes.", ["esst", "esse", "isst"], 1),
    Question("Ordne: Morgen / zur / ich / Schule / gehe", ["Ich gehe zur Schule morgen", "Morgen gehe ich zur Schule", "Zur Schule gehe ich morgen"], 1),
    Question("Was ist die Mehrzahl von 'Freund'?", ["Freunde", "Freunder", "Freunden"], 0),
]


class GermanTestController:
    def __init__(self, state: GameState, screen: pygame.Surface) -> None:
        self.state = state
        self.screen = screen
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 28)
        self.current_questions = random.sample(QUESTIONS, k=3)
        self.current_index = 0
        self.selected_option = 0
        self.correct_answers = 0
        self.completed = False
        self.feedback_timer = 0.0
        self.last_feedback = ""
        self.summary: List[str] = []
        self._config = get_balance_section("school")

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_option = (self.selected_option + 1) % len(self.current_question.options)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.selected_option = (self.selected_option - 1) % len(self.current_question.options)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._submit_answer()

    def update(self, dt: float) -> None:
        if self.feedback_timer > 0:
            self.feedback_timer -= dt
            if self.feedback_timer <= 0 and self.completed:
                self._apply_result()

    def render(self) -> None:
        self.screen.fill((20, 16, 16))
        if self.completed and self.feedback_timer <= 0:
            summary = self.font.render(f"Correct answers: {self.correct_answers}/ {len(self.current_questions)}", True, COLORS.text_light)
            self.screen.blit(summary, (80, 120))
            return

        question_surface = self.font.render(self.current_question.prompt, True, COLORS.text_light)
        self.screen.blit(question_surface, (80, 80))
        for idx, option in enumerate(self.current_question.options):
            color = COLORS.accent_ui if idx == self.selected_option else COLORS.text_light
            option_surface = self.small_font.render(f"{idx + 1}. {option}", True, color)
            self.screen.blit(option_surface, (100, 140 + idx * 40))

        if self.feedback_timer > 0:
            feedback_surface = self.small_font.render(self.last_feedback, True, COLORS.accent_fries)
            self.screen.blit(feedback_surface, (80, 280))

    @property
    def current_question(self) -> Question:
        return self.current_questions[self.current_index]

    def _submit_answer(self) -> None:
        correct = self.selected_option == self.current_question.correct_index
        if correct:
            self.correct_answers += 1
            self.last_feedback = random.choice(["Richtig!", "Sehr gut!", "Du hast es drauf!"])
        else:
            self.last_feedback = "Nicht ganz – merk dir die Regel!"
            self.state.apply_outcome(mood=-3.0)
        self.feedback_timer = 1.5
        self.current_index += 1
        if self.current_index >= len(self.current_questions):
            self.completed = True
            self.current_index = len(self.current_questions) - 1

    def _apply_result(self) -> None:
        total_questions = len(self.current_questions)
        if self.correct_answers >= total_questions - 0:
            cfg = self._config.get("quiz_pass", {})
            self.state.apply_outcome(
                mood=float(cfg.get("mood", 10.0)),
                german_xp=float(cfg.get("german_xp", 45.0)),
            )
            self.summary.append("Crushed the German quiz. Teacher almost smiled.")
            self.state.events.trigger("quiz_streak")
        elif self.correct_answers >= total_questions // 2:
            cfg = self._config.get("quiz_pass", {})
            self.state.apply_outcome(
                mood=float(cfg.get("mood", 6.0)) * 0.6,
                german_xp=float(cfg.get("german_xp", 45.0)) * 0.5,
            )
            self.summary.append("Passed the quiz with scrapes but still breathing.")
        else:
            fail_cfg = self._config.get("quiz_fail", {})
            self.state.apply_outcome(mood=float(fail_cfg.get("mood", -6.0)))
            self.summary.append("German grammar riot: quiz went sideways.")
            self.state.events.trigger("german_test_flunk")


__all__ = ["GermanTestController"]
