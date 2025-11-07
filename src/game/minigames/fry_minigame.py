"""Fry cooking minigame - dodge oil splashes and time flips."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List

import pygame

from game.balance import get_balance_section
from game.config import COLORS, TILE_HEIGHT, TILE_WIDTH
from game.state import GameState


@dataclass
class OilSplash:
    position: pygame.math.Vector2
    velocity: pygame.math.Vector2
    ttl: float


class FryMinigameController:
    def __init__(self, state: GameState, surface: pygame.Surface) -> None:
        self.state = state
        self.surface = surface
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 28)
        self.player_pos = pygame.math.Vector2(2, 2)
        self.fryer_tile = pygame.math.Vector2(3, 2)
        self.timer = 45.0
        config = get_balance_section("fry_minigame")
        self.flip_timer = random.uniform(3.5, 6.5)
        self.flip_window = float(config.get("flip_window", 1.0))
        self.flips_done = 0
        self.flips_needed = int(config.get("flips_needed", 3))
        self.oil_splashes: List[OilSplash] = []
        self.hit_counter = 0
        self.completed = False
        self.win = False
        self.summary: List[str] = []
        self._config = config

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            move = {pygame.K_w: (0, -1), pygame.K_s: (0, 1), pygame.K_a: (-1, 0), pygame.K_d: (1, 0)}.get(event.key)
            if move:
                self._move_player(pygame.math.Vector2(move))
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self._attempt_flip()

    def update(self, dt: float) -> None:
        if self.completed:
            return
        self.timer -= dt
        if self.timer <= 0:
            self._finish(False)
            return

        self.flip_timer -= dt
        if self.flip_timer <= 0:
            self._spawn_splashes()
            self.flip_timer = random.uniform(4.0, 7.0)

        for splash in list(self.oil_splashes):
            splash.ttl -= dt
            splash.position += splash.velocity * dt
            if splash.ttl <= 0:
                self.oil_splashes.remove(splash)
                continue
            if splash.position.distance_to(self.player_pos) < 0.5:
                self.hit_counter += 1
                penalty = float(self._config.get("hit_mood_penalty", -2.0))
                self.state.apply_outcome(mood=penalty)
                self.oil_splashes.remove(splash)

    def render(self) -> None:
        self.surface.fill((34, 24, 18))
        origin = (self.surface.get_width() // 2, 220)
        self._draw_grid(origin)
        self._draw_player(origin)
        self._draw_fryer(origin)
        self._draw_splashes(origin)
        timer_surface = self.font.render(f"Time: {int(self.timer)}", True, COLORS.text_light)
        flips_surface = self.font.render(f"Flips: {self.flips_done}/{self.flips_needed}", True, COLORS.accent_fries)
        hits_surface = self.small_font.render(f"Oil hits: {self.hit_counter}", True, COLORS.accent_ui)
        self.surface.blit(timer_surface, (80, 420))
        self.surface.blit(flips_surface, (80, 460))
        self.surface.blit(hits_surface, (80, 500))
        if self.completed:
            result = "Perfect fries!" if self.win else "Fries ruined"
            result_surface = self.font.render(result, True, COLORS.text_light)
            self.surface.blit(result_surface, (80, 560))

    def _draw_grid(self, origin: tuple[int, int]) -> None:
        for y in range(5):
            for x in range(6):
                cx = (x - y) * TILE_WIDTH // 2 + origin[0]
                cy = (x + y) * TILE_HEIGHT // 2 + origin[1]
                color = COLORS.warm_neutral if (x, y) != (3, 2) else COLORS.accent_fries
                points = [
                    (cx, cy - TILE_HEIGHT // 2),
                    (cx + TILE_WIDTH // 2, cy),
                    (cx, cy + TILE_HEIGHT // 2),
                    (cx - TILE_WIDTH // 2, cy)
                ]
                pygame.draw.polygon(self.surface, color, points)
                pygame.draw.polygon(self.surface, COLORS.warm_dark, points, 2)

    def _draw_player(self, origin: tuple[int, int]) -> None:
        px = (self.player_pos.x - self.player_pos.y) * TILE_WIDTH // 2 + origin[0]
        py = (self.player_pos.x + self.player_pos.y) * TILE_HEIGHT // 2 + origin[1] - 20
        pygame.draw.circle(self.surface, COLORS.accent_cool, (int(px), int(py)), 20)

    def _draw_fryer(self, origin: tuple[int, int]) -> None:
        fx = (self.fryer_tile.x - self.fryer_tile.y) * TILE_WIDTH // 2 + origin[0]
        fy = (self.fryer_tile.x + self.fryer_tile.y) * TILE_HEIGHT // 2 + origin[1] - 16
        pygame.draw.rect(self.surface, COLORS.warm_dark, (fx - 24, fy - 24, 48, 48))
        pygame.draw.rect(self.surface, COLORS.accent_fries, (fx - 20, fy - 20, 40, 40))

    def _draw_splashes(self, origin: tuple[int, int]) -> None:
        for splash in self.oil_splashes:
            sx = (splash.position.x - splash.position.y) * TILE_WIDTH // 2 + origin[0]
            sy = (splash.position.x + splash.position.y) * TILE_HEIGHT // 2 + origin[1] - 12
            pygame.draw.circle(self.surface, COLORS.accent_ui, (int(sx), int(sy)), 10)

    def _move_player(self, direction: pygame.math.Vector2) -> None:
        self.player_pos += direction
        self.player_pos.x = max(0, min(5, self.player_pos.x))
        self.player_pos.y = max(0, min(4, self.player_pos.y))

    def _attempt_flip(self) -> None:
        if self.completed:
            return
        distance = self.player_pos.distance_to(self.fryer_tile)
        if distance <= 1.1:
            if self.flip_timer <= self.flip_window:
                self.flips_done += 1
                self.state.apply_outcome(mood=4.0, hunger=8.0)
                if self.flips_done >= self.flips_needed:
                    self._finish(True)
            else:
                self.state.apply_outcome(mood=-2.0)
        else:
            self.state.apply_outcome(mood=-1.0)

    def _spawn_splashes(self) -> None:
        for _ in range(random.randint(1, 3)):
            start = self.fryer_tile + pygame.math.Vector2(random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3))
            angle = random.choice([(1, 1), (-1, 1), (1, -1), (-1, -1)])
            velocity = pygame.math.Vector2(angle).normalize() * random.uniform(1.8, 2.5)
            ttl = random.uniform(1.2, 1.8)
            self.oil_splashes.append(OilSplash(start, velocity, ttl))

    def _finish(self, success: bool) -> None:
        self.completed = True
        self.win = success
        if success:
            reward = self._config.get("success_reward", {})
            self.state.apply_outcome(
                mood=float(reward.get("mood", 8.0)),
                hunger=float(reward.get("hunger", 12.0)),
                energy=float(reward.get("energy", -5.0)),
            )
            self.summary.append("Crisp fries served with only minor grease casualties.")
            if self.hit_counter <= int(self._config.get("success_hits", 1)):
                self.state.events.trigger("perfect_fries_day")
                self.summary.append("Perfect fry form unlocked a confidence spark.")
        else:
            penalty = self._config.get("fail_penalty", {})
            self.state.apply_outcome(
                mood=float(penalty.get("mood", -6.0)),
                energy=float(penalty.get("energy", -8.0)),
            )
            self.state.events.trigger("grease_fire_close_call")
            self.summary.append("Grease fought back tonight. Bandages acquired.")
        self.summary.append(f"Oil hits taken: {self.hit_counter}")


__all__ = ["FryMinigameController"]
