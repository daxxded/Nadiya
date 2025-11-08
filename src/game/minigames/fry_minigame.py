"""Fry cooking minigame - dodge oil splashes and time flips with flair."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List

import pygame

from game.balance import get_balance_section
from game.config import COLORS, TILE_HEIGHT, TILE_WIDTH
from game.state import GameState
from game.ui.fonts import PixelFont
from game.ui.pixel_art import draw_kitchen_background, nadiya_sprite


@dataclass
class OilSplash:
    position: pygame.math.Vector2
    velocity: pygame.math.Vector2
    ttl: float


@dataclass
class OilTelegraph:
    position: pygame.math.Vector2
    ttl: float


class FryMinigameController:
    def __init__(self, state: GameState, surface: pygame.Surface) -> None:
        self.state = state
        self.surface = surface
        self.big_font = PixelFont(base_size=14, scale=3, bold=True)
        self.font = PixelFont(base_size=12, scale=2)
        self.small_font = PixelFont(base_size=10, scale=2)
        self.player_pos = pygame.math.Vector2(2.0, 2.0)
        self.fryer_tile = pygame.math.Vector2(3.0, 2.0)
        self.timer = 45.0
        config = get_balance_section("fry_minigame")
        self.flip_timer = random.uniform(3.5, 6.5)
        self.flip_window = float(config.get("flip_window", 1.0))
        self.flips_done = 0
        self.flips_needed = int(config.get("flips_needed", 3))
        self.oil_splashes: List[OilSplash] = []
        self.telegraphs: List[OilTelegraph] = []
        self.hit_counter = 0
        self.completed = False
        self.win = False
        self.summary: List[str] = []
        self._config = config
        self._key_state: dict[int, bool] = {}
        self._key_map = {
            pygame.K_w: pygame.math.Vector2(0, -1),
            pygame.K_s: pygame.math.Vector2(0, 1),
            pygame.K_a: pygame.math.Vector2(-1, 0),
            pygame.K_d: pygame.math.Vector2(1, 0),
            pygame.K_UP: pygame.math.Vector2(0, -1),
            pygame.K_DOWN: pygame.math.Vector2(0, 1),
            pygame.K_LEFT: pygame.math.Vector2(-1, 0),
            pygame.K_RIGHT: pygame.math.Vector2(1, 0),
        }
        self.move_speed = 2.8
        self.status_message = ""
        self.status_timer = 0.0
        self.flip_ready = False
        self.origin = (self.surface.get_width() // 2, 260)
        self.player_sprite = nadiya_sprite()
        self.background = pygame.Surface(self.surface.get_size())
        draw_kitchen_background(self.background)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in self._key_map:
                self._key_state[event.key] = True
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self._attempt_flip()
        elif event.type == pygame.KEYUP and event.key in self._key_state:
            self._key_state[event.key] = False

    def update(self, dt: float) -> None:
        if self.completed:
            return
        self.timer -= dt
        if self.timer <= 0:
            self._finish(False)
            return

        self._update_movement(dt)
        self.flip_timer -= dt
        if self.flip_timer <= 0:
            self._queue_splashes()
            self.flip_timer = random.uniform(4.0, 7.0)

        for telegraph in list(self.telegraphs):
            telegraph.ttl -= dt
            if telegraph.ttl <= 0:
                self.telegraphs.remove(telegraph)
                self._spawn_splash_at(telegraph.position)

        for splash in list(self.oil_splashes):
            splash.ttl -= dt
            splash.position += splash.velocity * dt
            if splash.ttl <= 0:
                self.oil_splashes.remove(splash)
                continue
            if splash.position.distance_to(self.player_pos) < 0.45:
                self.hit_counter += 1
                penalty = float(self._config.get("hit_mood_penalty", -2.0))
                self.state.apply_outcome(mood=penalty)
                self.oil_splashes.remove(splash)
                self.status_message = "Ouch! Hot oil sting."
                self.status_timer = 1.1

        distance = self.player_pos.distance_to(self.fryer_tile)
        self.flip_ready = distance <= 1.05 and self.flip_timer <= self.flip_window
        if not self.flip_ready and self.flip_timer <= self.flip_window and not self.status_message:
            self.status_message = "Get into position!"
            self.status_timer = 0.5

        if self.status_timer > 0:
            self.status_timer -= dt
            if self.status_timer <= 0:
                self.status_message = ""

    def render(self) -> None:
        self.surface.blit(self.background, (0, 0))
        self._draw_grid()
        self._draw_fryer()
        self._draw_telegraphs()
        self._draw_splashes()
        self._draw_player()
        timer_surface = self.big_font.render(f"Time {int(self.timer):02d}s", COLORS.text_light)
        flips_surface = self.big_font.render(f"Flips {self.flips_done}/{self.flips_needed}", COLORS.accent_fries)
        hits_surface = self.font.render(f"Oil hits: {self.hit_counter}", COLORS.accent_ui)
        self.surface.blit(timer_surface, (80, 420))
        self.surface.blit(flips_surface, (80, 470))
        self.surface.blit(hits_surface, (80, 520))
        if self.status_message:
            bubble = self.font.render(self.status_message, COLORS.text_light)
            rect = pygame.Surface((bubble.get_width() + 24, bubble.get_height() + 16), pygame.SRCALPHA)
            rect.fill((30, 24, 20, 210))
            rect.blit(bubble, (12, 8))
            self.surface.blit(rect, (self.surface.get_width() - rect.get_width() - 80, 420))
        if self.completed:
            result = "Perfect fries!" if self.win else "Fries ruined"
            result_surface = self.big_font.render(result, COLORS.text_light)
            self.surface.blit(result_surface, (80, 580))
        elif self.flip_ready:
            prompt = self.font.render("Space to flip!", COLORS.accent_fries)
            self.surface.blit(prompt, (self.surface.get_width() // 2 - prompt.get_width() // 2, 120))

    def _draw_grid(self) -> None:
        for y in range(5):
            for x in range(6):
                cx = (x - y) * TILE_WIDTH // 2 + self.origin[0]
                cy = (x + y) * TILE_HEIGHT // 2 + self.origin[1]
                color = (204, 186, 170)
                points = [
                    (cx, cy - TILE_HEIGHT // 2),
                    (cx + TILE_WIDTH // 2, cy),
                    (cx, cy + TILE_HEIGHT // 2),
                    (cx - TILE_WIDTH // 2, cy)
                ]
                pygame.draw.polygon(self.surface, color, points)
                pygame.draw.polygon(self.surface, COLORS.warm_dark, points, 1)

    def _draw_player(self) -> None:
        px = (self.player_pos.x - self.player_pos.y) * TILE_WIDTH // 2 + self.origin[0]
        py = (self.player_pos.x + self.player_pos.y) * TILE_HEIGHT // 2 + self.origin[1]
        sprite = self.player_sprite
        rect = sprite.get_rect()
        rect.midbottom = (int(px), int(py))
        self.surface.blit(sprite, rect)

    def _draw_fryer(self) -> None:
        fx = (self.fryer_tile.x - self.fryer_tile.y) * TILE_WIDTH // 2 + self.origin[0]
        fy = (self.fryer_tile.x + self.fryer_tile.y) * TILE_HEIGHT // 2 + self.origin[1]
        base_rect = pygame.Rect(fx - 28, fy - 34, 56, 48)
        pygame.draw.rect(self.surface, (80, 64, 54), base_rect, border_radius=6)
        inner = base_rect.inflate(-12, -12)
        pygame.draw.rect(self.surface, COLORS.accent_fries, inner, border_radius=6)
        if self.flip_ready:
            glow = inner.inflate(12, 12)
            pygame.draw.rect(self.surface, (255, 228, 120), glow, 3, border_radius=8)

    def _draw_splashes(self) -> None:
        for splash in self.oil_splashes:
            sx = (splash.position.x - splash.position.y) * TILE_WIDTH // 2 + self.origin[0]
            sy = (splash.position.x + splash.position.y) * TILE_HEIGHT // 2 + self.origin[1] - 8
            pygame.draw.circle(self.surface, COLORS.accent_ui, (int(sx), int(sy)), 10)

    def _draw_telegraphs(self) -> None:
        for telegraph in self.telegraphs:
            sx = (telegraph.position.x - telegraph.position.y) * TILE_WIDTH // 2 + self.origin[0]
            sy = (telegraph.position.x + telegraph.position.y) * TILE_HEIGHT // 2 + self.origin[1] - 12
            radius = max(6, int(16 + (telegraph.ttl / 0.7) * 8))
            pygame.draw.circle(self.surface, (255, 240, 180), (int(sx), int(sy)), radius, 2)

    def _update_movement(self, dt: float) -> None:
        direction = pygame.math.Vector2(0, 0)
        for key, vector in self._key_map.items():
            if self._key_state.get(key):
                direction += vector
        if direction.length_squared() > 0:
            direction = direction.normalize()
            self.player_pos += direction * self.move_speed * dt
            self.player_pos.x = max(0.0, min(5.0, self.player_pos.x))
            self.player_pos.y = max(0.0, min(4.0, self.player_pos.y))

    def _attempt_flip(self) -> None:
        if self.completed:
            return
        distance = self.player_pos.distance_to(self.fryer_tile)
        if distance <= 1.1:
            if self.flip_timer <= self.flip_window:
                self.flips_done += 1
                self.state.apply_outcome(mood=4.0, hunger=8.0)
                self.status_message = "Nice timing!"
                self.status_timer = 1.4
                if self.flips_done >= self.flips_needed:
                    self._finish(True)
            else:
                self.state.apply_outcome(mood=-2.0)
                self.status_message = "Too early – soggy fries."
                self.status_timer = 1.2
        else:
            self.state.apply_outcome(mood=-1.0)
            self.status_message = "Get closer to the fryer."
            self.status_timer = 1.2

    def _queue_splashes(self) -> None:
        for _ in range(random.randint(1, 3)):
            start = self.fryer_tile + pygame.math.Vector2(random.uniform(-0.35, 0.35), random.uniform(-0.35, 0.35))
            self.telegraphs.append(OilTelegraph(start, 0.7))

    def _spawn_splash_at(self, position: pygame.math.Vector2) -> None:
        angle = random.choice([(1, 1), (-1, 1), (1, -1), (-1, -1)])
        velocity = pygame.math.Vector2(angle).normalize() * random.uniform(1.8, 2.4)
        ttl = random.uniform(1.1, 1.8)
        self.oil_splashes.append(OilSplash(position, velocity, ttl))

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
        self.status_message = ""


__all__ = ["FryMinigameController"]
