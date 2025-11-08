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
from game.scenes.transition import TransitionScene
from game.state import GameState, TimeSegment
from game.ui.hud import HUD
from game.ui.settings import SettingsOverlay


class SceneController:
    def __init__(self, state: GameState, screen: pygame.Surface, ai_client: LocalAIClient) -> None:
        self.state = state
        self.screen = screen
        self.ai_client = ai_client
        self.hud = HUD(screen)
        self.settings_overlay = SettingsOverlay(state, ai_client, screen)
        self.active_scene: Scene | None = None
        self.transition_scene: TransitionScene | None = None
        self._pending_segment: TimeSegment | None = None
        self._pending_factory: Callable[[], Scene] | None = None
        self.clock = pygame.time.Clock()
        self.state.start_segment(self.state.segment)
        self._switch_scene(TimeSegment.MORNING)

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
        if isinstance(self.active_scene, MomScene):
            factory = lambda: SleepScene(self.state, self.screen)
            next_segment = TimeSegment.NIGHT
        elif isinstance(self.active_scene, SleepScene):
            next_segment = self.state.segment
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
        if segment == TimeSegment.MORNING:
            self.active_scene = SchoolScene(self.state, self.screen)
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
