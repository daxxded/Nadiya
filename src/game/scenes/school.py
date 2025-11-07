"""School morning segment combining hallway dodge and German test."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List

import pygame

from game.balance import get_balance_section
from game.config import COLORS, TILE_HEIGHT, TILE_WIDTH
from game.minigames.german_test import GermanTestController
from game.scenes.base import Scene
from game.state import GameState


@dataclass
class NPC:
    grid_pos: pygame.math.Vector2
    direction: int
    speed: float
    annoying: bool


class SchoolScene(Scene):
    def __init__(self, state: GameState, screen: pygame.Surface) -> None:
        super().__init__(state)
        self.screen = screen
        self.font = pygame.font.Font(None, 32)
        self.player_pos = pygame.math.Vector2(2, 4)
        self.player_speed = 4.0
        self.npcs: List[NPC] = []
        self.timer = float(get_balance_section("segments")["morning"].get("base_timer", 28))
        self.test_controller: GermanTestController | None = None
        self.in_test = False
        self._spawn_npcs()
        self._school_cfg = get_balance_section("school")
        self.summary: List[str] = []
        self.collisions_today = 0
        self._map_width = 6
        self._map_height = 6
        self._walls = {(x, 5) for x in range(self._map_width)}

    def on_enter(self) -> None:
        morning_cfg = get_balance_section("segments")["morning"]
        self.state.stats.apply_energy(-float(morning_cfg.get("energy_cost", 8)))

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.in_test and self.test_controller:
            self.test_controller.handle_event(event)
            return
        if event.type == pygame.KEYDOWN:
            direction = None
            if event.key in (pygame.K_w, pygame.K_UP):
                direction = pygame.math.Vector2(0, -1)
            elif event.key in (pygame.K_s, pygame.K_DOWN):
                direction = pygame.math.Vector2(0, 1)
            elif event.key in (pygame.K_a, pygame.K_LEFT):
                direction = pygame.math.Vector2(-1, 0)
            elif event.key in (pygame.K_d, pygame.K_RIGHT):
                direction = pygame.math.Vector2(1, 0)
            if direction is not None:
                self._move_player(direction)

    def update(self, dt: float) -> None:
        if self.in_test and self.test_controller:
            self.test_controller.update(dt)
            if self.test_controller.completed and self.test_controller.feedback_timer <= 0:
                if self.test_controller.summary:
                    self.summary.extend(self.test_controller.summary)
                self.completed = True
            return

        self.timer -= dt
        if self.timer <= 0:
            self._start_test()
            return

        for npc in list(self.npcs):
            npc.grid_pos.x += npc.speed * dt * npc.direction
            if npc.grid_pos.x < 0:
                npc.grid_pos.x = 5
            elif npc.grid_pos.x > 5:
                npc.grid_pos.x = 0
            if npc.grid_pos.distance_to(self.player_pos) < 0.4:
                self._handle_collision(npc)

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((24, 24, 30))
        if self.in_test and self.test_controller:
            self.test_controller.render()
            return
        origin = (surface.get_width() // 2, 180)
        for y in range(self._map_height):
            for x in range(self._map_width):
                cx = (x - y) * TILE_WIDTH // 2 + origin[0]
                cy = (x + y) * TILE_HEIGHT // 2 + origin[1]
                if (x, y) in self._walls:
                    color = (60, 52, 68)
                else:
                    color = COLORS.warm_neutral if y < self._map_height - 1 else COLORS.accent_cool
                points = [
                    (cx, cy - TILE_HEIGHT // 2),
                    (cx + TILE_WIDTH // 2, cy),
                    (cx, cy + TILE_HEIGHT // 2),
                    (cx - TILE_WIDTH // 2, cy)
                ]
                pygame.draw.polygon(surface, color, points)
                pygame.draw.polygon(surface, COLORS.warm_dark, points, 1)

        self._draw_player(origin)
        for npc in self.npcs:
            self._draw_npc(origin, npc)

        timer_surface = self.font.render(f"Reach class in {int(self.timer)}s", True, COLORS.text_light)
        surface.blit(timer_surface, (80, 460))

    def _spawn_npcs(self) -> None:
        self.npcs.clear()
        for y in range(0, 4):
            for _ in range(2):
                pos = pygame.math.Vector2(random.randint(0, 5), y + random.uniform(-0.2, 0.2))
                npc = NPC(pos, random.choice([-1, 1]), random.uniform(0.5, 1.2), random.random() < 0.4)
                self.npcs.append(npc)

    def _move_player(self, direction: pygame.math.Vector2) -> None:
        target = self.player_pos + direction
        if 0 <= target.x < self._map_width and 0 <= target.y < self._map_height:
            if (int(target.x), int(target.y)) not in self._walls:
                self.player_pos = target

    def _draw_player(self, origin: tuple[int, int]) -> None:
        px = (self.player_pos.x - self.player_pos.y) * TILE_WIDTH // 2 + origin[0]
        py = (self.player_pos.x + self.player_pos.y) * TILE_HEIGHT // 2 + origin[1] - 18
        pygame.draw.circle(self.screen, COLORS.accent_ui, (int(px), int(py)), 20)

    def _draw_npc(self, origin: tuple[int, int], npc: NPC) -> None:
        nx = (npc.grid_pos.x - npc.grid_pos.y) * TILE_WIDTH // 2 + origin[0]
        ny = (npc.grid_pos.x + npc.grid_pos.y) * TILE_HEIGHT // 2 + origin[1] - 16
        color = COLORS.accent_fries if npc.annoying else COLORS.warm_dark
        pygame.draw.circle(self.screen, color, (int(nx), int(ny)), 16)

    def _handle_collision(self, npc: NPC) -> None:
        self.npcs.remove(npc)
        self.collisions_today += 1
        if npc.annoying:
            mood_delta = float(self._school_cfg.get("annoying_collision", {}).get("mood", -5.0))
            timer_delta = float(self._school_cfg.get("annoying_collision", {}).get("timer", -2.0))
            self.state.apply_outcome(mood=mood_delta)
            self.timer += timer_delta
            if self.collisions_today >= int(get_balance_section("events").get("bad_school_collisions", 3)):
                self.state.events.trigger("bad_school_day")
                self.summary.append("Hallway gauntlet went poorly; gossip swelled.")
        else:
            bonus = float(self._school_cfg.get("friendly_collision", {}).get("mood", 2.0))
            self.state.apply_outcome(mood=bonus)
            self.summary.append("A classmate actually cheered you on.")

    def _start_test(self) -> None:
        self.in_test = True
        self.test_controller = GermanTestController(self.state, self.screen)
        self.summary.append("Made it to class; quiz panic engaged.")


__all__ = ["SchoolScene"]
