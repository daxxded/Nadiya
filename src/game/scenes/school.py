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
from game.ui.fonts import PixelFont
from game.ui.pixel_art import classmate_variants, draw_school_background, nadiya_sprite


@dataclass
class NPC:
    grid_pos: pygame.math.Vector2
    direction: int
    speed: float
    annoying: bool
    sprite: pygame.Surface


class SchoolScene(Scene):
    def __init__(self, state: GameState, screen: pygame.Surface) -> None:
        super().__init__(state)
        self.screen = screen
        self.small_font = PixelFont(base_size=10, scale=2)
        self.font = PixelFont(base_size=12, scale=2)
        self.big_font = PixelFont(base_size=14, scale=3, bold=True)
        self.player_pos = pygame.math.Vector2(2.5, 4.5)
        self.player_sprite = nadiya_sprite()
        self.player_speed = 2.8
        self.npcs: List[NPC] = []
        self.timer = float(get_balance_section("segments")["morning"].get("base_timer", 32))
        self.test_controller: GermanTestController | None = None
        self.in_test = False
        self.classmate_sprites = classmate_variants()
        self._map_width = 6
        self._map_height = 6
        self._walls = {(x, 5) for x in range(self._map_width)}
        self._school_cfg = get_balance_section("school")
        self.summary: List[str] = []
        self.collisions_today = 0
        self._spawn_npcs()
        self._input: dict[int, bool] = {}
        self.origin = (self.screen.get_width() // 2, 240)
        self.background = pygame.Surface(self.screen.get_size())
        draw_school_background(self.background)
        self.status_message = ""
        self.status_timer = 0.0

    def on_enter(self) -> None:
        morning_cfg = get_balance_section("segments")["morning"]
        self.state.stats.apply_energy(-float(morning_cfg.get("energy_cost", 8)))

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.in_test and self.test_controller:
            self.test_controller.handle_event(event)
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_w, pygame.K_UP, pygame.K_s, pygame.K_DOWN, pygame.K_a, pygame.K_LEFT, pygame.K_d, pygame.K_RIGHT):
                self._input[event.key] = True
        elif event.type == pygame.KEYUP:
            if event.key in self._input:
                self._input[event.key] = False

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

        self._update_player(dt)
        for npc in list(self.npcs):
            npc.grid_pos.x += npc.speed * dt * npc.direction
            if npc.grid_pos.x < -0.5:
                npc.grid_pos.x = self._map_width - 0.5
            elif npc.grid_pos.x > self._map_width - 0.5:
                npc.grid_pos.x = -0.5
            if npc.grid_pos.distance_to(self.player_pos) < 0.5:
                self._handle_collision(npc)

        if self.status_timer > 0:
            self.status_timer -= dt
            if self.status_timer <= 0:
                self.status_message = ""

    def render(self, surface: pygame.Surface) -> None:
        surface.blit(self.background, (0, 0))
        if self.in_test and self.test_controller:
            self.test_controller.render()
            return
        self._draw_grid(surface)
        self._draw_player(surface)
        for npc in self.npcs:
            self._draw_npc(surface, npc)
        timer_surface = self.big_font.render(f"Reach class in {int(self.timer):02d}s", COLORS.text_light)
        surface.blit(timer_surface, (80, 460))
        if self.status_message:
            bubble = self.font.render(self.status_message, COLORS.accent_fries)
            surface.blit(bubble, (80, 500))

    def _spawn_npcs(self) -> None:
        self.npcs.clear()
        sprites = self.classmate_sprites
        for y in range(0, 4):
            for _ in range(2):
                pos = pygame.math.Vector2(random.uniform(0, self._map_width - 1), y + random.uniform(-0.2, 0.2))
                npc = NPC(pos, random.choice([-1, 1]), random.uniform(0.6, 1.3), random.random() < 0.4, random.choice(sprites))
                self.npcs.append(npc)

    def _update_player(self, dt: float) -> None:
        direction = pygame.math.Vector2(0, 0)
        if self._input.get(pygame.K_w) or self._input.get(pygame.K_UP):
            direction += pygame.math.Vector2(0, -1)
        if self._input.get(pygame.K_s) or self._input.get(pygame.K_DOWN):
            direction += pygame.math.Vector2(0, 1)
        if self._input.get(pygame.K_a) or self._input.get(pygame.K_LEFT):
            direction += pygame.math.Vector2(-1, 0)
        if self._input.get(pygame.K_d) or self._input.get(pygame.K_RIGHT):
            direction += pygame.math.Vector2(1, 0)
        if direction.length_squared() > 0:
            direction = direction.normalize()
            speed = self.player_speed * self.state.fatigue_modifier()
            target = self.player_pos + direction * speed * dt
            if self._is_walkable(target):
                self.player_pos = target

    def _draw_grid(self, surface: pygame.Surface) -> None:
        for y in range(self._map_height):
            for x in range(self._map_width):
                cx = (x - y) * TILE_WIDTH // 2 + self.origin[0]
                cy = (x + y) * TILE_HEIGHT // 2 + self.origin[1]
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

    def _draw_player(self, surface: pygame.Surface) -> None:
        px = (self.player_pos.x - self.player_pos.y) * TILE_WIDTH // 2 + self.origin[0]
        py = (self.player_pos.x + self.player_pos.y) * TILE_HEIGHT // 2 + self.origin[1]
        sprite = self.player_sprite
        rect = sprite.get_rect()
        rect.midbottom = (int(px), int(py))
        surface.blit(sprite, rect)
        highlight = pygame.Surface((sprite.get_width() + 12, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(highlight, (0, 0, 0, 120), highlight.get_rect())
        highlight_rect = highlight.get_rect()
        highlight_rect.center = (rect.centerx, rect.bottom)
        surface.blit(highlight, highlight_rect)

    def _draw_npc(self, surface: pygame.Surface, npc: NPC) -> None:
        nx = (npc.grid_pos.x - npc.grid_pos.y) * TILE_WIDTH // 2 + self.origin[0]
        ny = (npc.grid_pos.x + npc.grid_pos.y) * TILE_HEIGHT // 2 + self.origin[1]
        sprite = npc.sprite
        rect = sprite.get_rect()
        rect.midbottom = (int(nx), int(ny))
        surface.blit(sprite, rect)
        if npc.annoying:
            label = self.small_font.render("!", COLORS.accent_ui)
            surface.blit(label, (rect.centerx - label.get_width() // 2, rect.top - 10))

    def _handle_collision(self, npc: NPC) -> None:
        self.npcs.remove(npc)
        self.collisions_today += 1
        if npc.annoying:
            mood_delta = float(self._school_cfg.get("annoying_collision", {}).get("mood", -5.0))
            timer_delta = float(self._school_cfg.get("annoying_collision", {}).get("timer", -2.0))
            self.state.apply_outcome(mood=mood_delta)
            self.timer += timer_delta
            self.status_message = "They blocked you on purpose."
            self.status_timer = 1.5
            if self.collisions_today >= int(get_balance_section("events").get("bad_school_collisions", 3)):
                self.state.events.trigger("bad_school_day")
                self.summary.append("Hallway gauntlet went poorly; gossip swelled.")
        else:
            bonus = float(self._school_cfg.get("friendly_collision", {}).get("mood", 2.0))
            self.state.apply_outcome(mood=bonus)
            self.summary.append("A classmate actually cheered you on.")
            self.status_message = "Quick high-five in the hallway."
            self.status_timer = 1.3

    def _start_test(self) -> None:
        self.in_test = True
        self.test_controller = GermanTestController(self.state, self.screen)
        self.summary.append("Made it to class; quiz panic engaged.")

    def _is_walkable(self, position: pygame.math.Vector2) -> bool:
        grid_x = int(round(position.x))
        grid_y = int(round(position.y))
        if not (0 <= grid_x < self._map_width and 0 <= grid_y < self._map_height):
            return False
        if (grid_x, grid_y) in self._walls:
            return False
        return True


__all__ = ["SchoolScene"]
