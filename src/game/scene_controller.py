"""Scene orchestration for the daily loop."""

from __future__ import annotations

from typing import Callable

import pygame

from game.ai.local_client import LocalAIClient
from game.config import FPS
from game.scenes.base import Scene
from game.scenes.home import HomeScene
from game.scenes.mom import MomScene
from game.scenes.school import SchoolScene
from game.scenes.sleep import SleepScene
from game.scenes.tram import TramScene
from game.scenes.transition import TransitionScene
from game.state import GameState, TimeSegment
from game.ui.hud import HUD
from game.ui.settings import SettingsOverlay


class SceneController:
    def __init__(self, state: GameState, screen: pygame.Surface, ai_client: LocalAIClient) -> None:
        self.state = state
        self.screen = screen
        self.ai_client = ai_client
        pygame.key.set_repeat(280, 45)
        self.hud = HUD(screen)
        self.settings_overlay = SettingsOverlay(state, ai_client, screen)
        self.active_scene: Scene | None = None
        self.transition_scene: TransitionScene | None = None
        self._pending_segment: TimeSegment | None = None
        self._pending_factory: Callable[[], Scene] | None = None
        self.clock = pygame.time.Clock()
        self.state.start_segment(TimeSegment.DAWN)
        self.active_scene = HomeScene(
            self.state,
            self.screen,
            self.ai_client,
            mode="dawn",
        )
        self.active_scene.on_enter()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and pygame.key.get_mods() & pygame.KMOD_CTRL:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
            return
        if self.settings_overlay.active:
            self.settings_overlay.handle_event(event)
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.settings_overlay.toggle()
            return
        if self.transition_scene:
            self.transition_scene.handle_event(event)
            return
        if self.active_scene:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.hud.skip_rect:
                if self.hud.skip_rect.collidepoint(event.pos):
                    self.state.request_skip()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p and hasattr(self.active_scene, "toggle_phone"):
                dialogue = getattr(self.active_scene, "dialogue", None)
                vending = getattr(self.active_scene, "vending", None)
                if dialogue and getattr(dialogue, "active", False):
                    return
                if vending and getattr(vending, "active", False):
                    return
                self.active_scene.toggle_phone()
                return
            self.active_scene.handle_event(event)

    def update(self) -> None:
        dt = self.clock.tick(FPS) / 1000.0
        if self.settings_overlay.active:
            self._render()
            return
        if self.transition_scene:
            self.transition_scene.update(dt)
            if self.transition_scene.completed:
                self.transition_scene = None
                self._activate_pending()
            self._render()
            return
        if self.active_scene:
            self.state.tick_clock(dt)
            if self.state.consume_skip_request():
                self.active_scene.skip_to_next()
            self.active_scene.update(dt)
            if self.active_scene.completed:
                self._advance()
        self._render()

    def _render(self) -> None:
        if self.active_scene:
            self.active_scene.render(self.screen)
        if self.transition_scene:
            self.transition_scene.render(self.screen)
        self.hud.render(self.state)
        if self.settings_overlay.active:
            self.settings_overlay.render()
        pygame.display.flip()

    def _advance(self) -> None:
        if not self.active_scene:
            return
        summary = self.active_scene.get_summary()
        next_segment = self.state.segment
        factory = None
        if isinstance(self.active_scene, HomeScene):
            if self.active_scene.mode == "dawn":
                next_segment = TimeSegment.COMMUTE
                factory = lambda: TramScene(
                    self.state,
                    self.screen,
                    direction="to school",
                    target_segment=TimeSegment.MORNING,
                )
            elif self.active_scene.mode == "afternoon":
                next_segment = TimeSegment.EVENING
            elif self.active_scene.mode == "evening":
                next_segment = TimeSegment.NIGHT
        elif isinstance(self.active_scene, MomScene):
            factory = lambda: SleepScene(self.state, self.screen)
            next_segment = TimeSegment.NIGHT
        elif isinstance(self.active_scene, SleepScene):
            next_segment = TimeSegment.DAWN
        elif isinstance(self.active_scene, SchoolScene):
            next_segment = TimeSegment.COMMUTE
            factory = lambda: TramScene(self.state, self.screen, direction="home", target_segment=TimeSegment.AFTERNOON)
        elif isinstance(self.active_scene, TramScene):
            next_segment = self.active_scene.target_segment
        else:
            self.state.advance_segment()
            next_segment = self.state.segment
            if self.state.should_force_rest() and next_segment != TimeSegment.NIGHT:
                summary = list(summary) + ["Body begged for rest; skipping ahead to night."]
                next_segment = TimeSegment.NIGHT
                self.state.segment = TimeSegment.NIGHT
                self.state.events.trigger("forced_rest")
                factory = lambda: SleepScene(self.state, self.screen)
        self._queue_transition(summary, next_segment, factory)

    def _switch_scene(self, segment: TimeSegment) -> None:
        if self.active_scene:
            self.active_scene.on_exit()
        self.state.start_segment(segment)
        if segment == TimeSegment.DAWN:
            self.active_scene = HomeScene(
                self.state,
                self.screen,
                self.ai_client,
                mode="dawn",
            )
        elif segment == TimeSegment.COMMUTE:
            self.active_scene = TramScene(
                self.state,
                self.screen,
                direction="to school",
                target_segment=TimeSegment.MORNING,
            )
        elif segment == TimeSegment.MORNING:
            self.active_scene = SchoolScene(self.state, self.screen, self.ai_client)
        elif segment == TimeSegment.AFTERNOON:
            self.active_scene = HomeScene(
                self.state, self.screen, self.ai_client, mode="afternoon"
            )
        elif segment == TimeSegment.EVENING:
            self.active_scene = HomeScene(
                self.state, self.screen, self.ai_client, mode="evening"
            )
        elif segment == TimeSegment.NIGHT:
            self.active_scene = MomScene(self.state, self.ai_client, self.screen)
        else:
            self.active_scene = SleepScene(self.state, self.screen)
        self.active_scene.on_enter()

    def _queue_transition(self, summary: list[str], next_segment: TimeSegment, factory: Callable[[], Scene] | None) -> None:
        self._pending_segment = next_segment
        self._pending_factory = factory
        self.state.start_segment(next_segment)
        self.transition_scene = TransitionScene(
            self.state,
            self.screen,
            summary=summary,
            next_segment=next_segment,
        )
        self.transition_scene.on_enter()

    def _activate_pending(self) -> None:
        if self._pending_factory:
            self.active_scene = self._pending_factory()
            self._pending_factory = None
            if self.active_scene:
                self.active_scene.on_enter()
            return
        if self._pending_segment:
            self._switch_scene(self._pending_segment)
            self._pending_segment = None


__all__ = ["SceneController"]
