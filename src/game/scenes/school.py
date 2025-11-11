"""Expanded school scene with exterior, hallway, and classroom phases."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Sequence

import random

import pygame

from game.ai.local_client import LocalAIClient
from game.balance import get_balance_section
from game.config import COLORS, TILE_HEIGHT, TILE_WIDTH
from game.minigames.german_test import GermanTestController
from game.scenes.base import Scene
from game.state import GameState
from game.scenes.isometric import iso_to_screen
from game.ui.dialogue_overlay import DialogueOverlay
from game.ui.fonts import PixelFont
from game.ui.phone import PhoneOverlay
from game.ui.pixel_art import (
    classmate_variants,
    draw_school_exterior,
    draw_school_hallway,
    draw_school_lobby,
    nadiya_sprite,
)
from game.ui.vending import VendingMachineUI


@dataclass
class SchoolNPC:
    name: str
    position: pygame.math.Vector2
    sprite: pygame.Surface
    ai_persona: Optional[str] = None
    lines: Sequence[str] = ()
    roam: tuple[pygame.math.Vector2, pygame.math.Vector2] | None = None
    speed: float = 0.4
    direction: int = 1


class Phase(Enum):
    EXTERIOR = auto()
    HALLWAY = auto()
    CLASS = auto()


class SchoolScene(Scene):
    """Multi-phase morning segment combining exploration and quizzes."""

    def __init__(self, state: GameState, screen: pygame.Surface, ai_client: LocalAIClient) -> None:
        super().__init__(state)
        self.screen = screen
        self.ai_client = ai_client
        self.font = PixelFont(base_size=12, scale=2)
        self.small_font = PixelFont(base_size=10, scale=2)
        self.player_sprite = nadiya_sprite()
        self.player_pos = pygame.math.Vector2(6.0, 6.0)
        self.player_speed = 2.6
        self.phone = PhoneOverlay(state, ai_client, screen)
        self.dialogue = DialogueOverlay(state, ai_client, screen)
        self.vending = VendingMachineUI(state, screen)
        self.phase = Phase.EXTERIOR
        self.phase_elapsed = 0.0
        self.phase_order = [Phase.EXTERIOR, Phase.HALLWAY, Phase.CLASS]
        self._phase_cfg = get_balance_section("school").get("phases", {})
        self.phase_durations = {
            Phase.EXTERIOR: float(self._phase_cfg.get("exterior_seconds", 900.0)),
            Phase.HALLWAY: float(self._phase_cfg.get("hallway_seconds", 300.0)),
            Phase.CLASS: float(self._phase_cfg.get("class_seconds", 900.0)),
        }
        self.origin = (0, 0)
        self.world_surface = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        self.camera_rect = pygame.Rect(0, 0, self.screen.get_width(), self.screen.get_height())
        self.npcs: List[SchoolNPC] = []
        self.classmate_sprites = classmate_variants()
        self.summary: List[str] = []
        self._input: dict[int, bool] = {}
        self._map_size = (14, 10)
        self._walls: set[tuple[int, int]] = set()
        self._background = pygame.Surface(self.world_surface.get_size())
        self.test_controller: Optional[GermanTestController] = None
        self.teacher_lines: List[str] = []
        self.teacher_timer = 0.0
        self.self_talk_timer = random.uniform(28.0, 52.0)
        self.self_talk_duration = 0.0
        self.self_talk_message = ""
        self._prepare_phase(self.phase)

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.test_controller:
            self.test_controller.handle_event(event)
            return
        if self.phone.active:
            self.phone.handle_event(event)
            return
        if self.dialogue.active:
            self.dialogue.handle_event(event)
            return
        if self.vending.active:
            self.vending.handle_event(event)
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_w, pygame.K_UP, pygame.K_s, pygame.K_DOWN, pygame.K_a, pygame.K_LEFT, pygame.K_d, pygame.K_RIGHT):
                self._input[event.key] = True
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                npc = self._nearby_npc()
                if npc:
                    self._interact_npc(npc)
                elif self.phase == Phase.HALLWAY:
                    if self._player_near_vending():
                        self.vending.open()
                        return
        elif event.type == pygame.KEYUP and event.key in self._input:
            self._input[event.key] = False

    def update(self, dt: float) -> None:
        if self.test_controller:
            self.test_controller.update(dt)
            if self.test_controller.completed and self.test_controller.feedback_timer <= 0:
                if self.test_controller.summary:
                    self.summary.extend(self.test_controller.summary)
                self.completed = True
            return
        self.phone.update(dt)
        self.dialogue.update(dt)
        self.vending.update(dt)
        if self.phone.active or self.dialogue.active or self.vending.active:
            return
        if self.phase == Phase.CLASS and self.teacher_timer > 0:
            self.teacher_timer -= dt
            self.phase_elapsed += dt
            self._sync_clock_progress()
            if self.teacher_timer <= 0 and not self.test_controller:
                self.test_controller = GermanTestController(self.state, self.screen)
            return
        self._update_player(dt)
        self._update_npcs(dt)
        self._update_self_talk(dt)
        self.phase_elapsed += dt
        self._sync_clock_progress()
        if self.phase_elapsed >= self.phase_durations[self.phase]:
            self._advance_phase()

    def render(self, surface: pygame.Surface) -> None:
        if self.test_controller:
            self.test_controller.render()
            return
        self.world_surface.blit(self._background, (0, 0))
        if self.phase == Phase.CLASS and self.teacher_timer > 0:
            self._draw_grid(self.world_surface)
            self._draw_player(self.world_surface)
            camera = self._camera_rect_view()
            surface.blit(self.world_surface, (0, 0), camera)
            for idx, line in enumerate(self.teacher_lines):
                text = self.font.render(line, COLORS.text_light)
                surface.blit(text, (80, 120 + idx * 36))
            return
        self._draw_grid(self.world_surface)
        self._draw_vending(self.world_surface)
        self._draw_npcs(self.world_surface)
        self._draw_player(self.world_surface)
        self._draw_self_talk(self.world_surface)
        camera = self._camera_rect_view()
        surface.blit(self.world_surface, (0, 0), camera)
        self._draw_prompts(surface)
        if self.phone.active:
            self.phone.render()
        if self.dialogue.active:
            self.dialogue.render()
        if self.vending.active:
            self.vending.render()

    def get_summary(self) -> list[str]:
        vending_lines = self.vending.consume_summary()
        if vending_lines:
            self.summary.extend(vending_lines)
        dialogue_lines = self.dialogue.consume_summary()
        if dialogue_lines:
            self.summary.extend(dialogue_lines)
        return super().get_summary()

    def skip_to_next(self) -> None:
        if self.phase == Phase.CLASS:
            if self.test_controller:
                self.test_controller.force_finish()
            else:
                self.completed = True
            return
        self.phase_elapsed = self.phase_durations[self.phase]
        self._advance_phase()

    def toggle_phone(self) -> None:
        if self.phone.active:
            self.phone.close()
        else:
            self.phone.open()
            self.phone.active_app = "discord"

    def _prepare_phase(self, phase: Phase) -> None:
        self.phase = phase
        self.phase_elapsed = 0.0
        self._input.clear()
        if phase == Phase.EXTERIOR:
            self._map_size = (18, 12)
            self._walls = set()
            self._configure_world(self._map_size)
            draw_school_exterior(self._background)
            self.player_pos = pygame.math.Vector2(9.0, 9.0)
            self.npcs = self._build_exterior_npcs()
            self.teacher_lines.clear()
        elif phase == Phase.HALLWAY:
            self._map_size = (22, 6)
            self._walls = {(x, 0) for x in range(self._map_size[0])} | {(x, self._map_size[1] - 1) for x in range(self._map_size[0])}
            self._configure_world(self._map_size)
            draw_school_hallway(self._background)
            self.player_pos = pygame.math.Vector2(4.0, 3.0)
            self.npcs = self._build_hallway_npcs()
        else:
            self._map_size = (10, 8)
            self._configure_world(self._map_size)
            draw_school_lobby(self._background)
            self.player_pos = pygame.math.Vector2(5.0, 5.0)
            self.npcs = []
            self._start_class_sequence()
        self._camera_rect_view()

    def _advance_phase(self) -> None:
        current_index = self.phase_order.index(self.phase)
        if current_index >= len(self.phase_order) - 1:
            if not self.test_controller:
                self._start_class_sequence()
            return
        next_phase = self.phase_order[current_index + 1]
        if self.phase == Phase.EXTERIOR:
            self.summary.append("Caught the 8:30 bell and headed inside.")
        elif self.phase == Phase.HALLWAY:
            self.summary.append("Bell rang; time for German.")
        self._prepare_phase(next_phase)

    def _start_class_sequence(self) -> None:
        self.teacher_lines = [
            "Lehrer: Guten Morgen! Heute reden wir über trennbare Verben.",
            "Lehrer: Erst eine kurze Wiederholung, dann ein Quiz.",
        ]
        self.teacher_timer = 4.0
        self.test_controller = None

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
        if direction.length_squared() == 0:
            return
        direction = direction.normalize()
        speed = self.player_speed * self.state.fatigue_modifier()
        target = self.player_pos + direction * speed * dt
        if self._is_walkable(target):
            self.player_pos = target
            self._camera_rect_view()

    def _update_npcs(self, dt: float) -> None:
        for npc in self.npcs:
            if not npc.roam:
                continue
            start, end = npc.roam
            target = end if npc.direction > 0 else start
            delta = target - npc.position
            if delta.length_squared() < 0.05:
                npc.direction *= -1
                continue
            npc.position += delta.normalize() * npc.speed * dt

    def _sync_clock_progress(self) -> None:
        elapsed_total = sum(
            self.phase_durations[p]
            for p in self.phase_order
            if self.phase_order.index(p) < self.phase_order.index(self.phase)
        ) + self.phase_elapsed
        self.state.segment_time = min(elapsed_total, self.state.segment_duration)

    def _draw_grid(self, surface: pygame.Surface) -> None:
        width, height = self._map_size
        for y in range(height):
            for x in range(width):
                cx, cy = self._project_tile(x, y)
                points = [
                    (cx, cy - TILE_HEIGHT // 2),
                    (cx + TILE_WIDTH // 2, cy),
                    (cx, cy + TILE_HEIGHT // 2),
                    (cx - TILE_WIDTH // 2, cy),
                ]
                if (x, y) in self._walls:
                    color = (56, 48, 72)
                else:
                    color = (78, 68, 96) if self.phase != Phase.EXTERIOR else (70, 84, 92)
                pygame.draw.polygon(surface, color, points)
                pygame.draw.polygon(surface, COLORS.warm_dark, points, 1)

    def _draw_player(self, surface: pygame.Surface) -> None:
        px, py = self._project_point(self.player_pos)
        rect = self.player_sprite.get_rect()
        rect.midbottom = (int(px), int(py))
        surface.blit(self.player_sprite, rect)
        shadow = pygame.Surface((self.player_sprite.get_width(), 8), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 120), shadow.get_rect())
        shadow_rect = shadow.get_rect()
        shadow_rect.midtop = (rect.centerx, rect.bottom - 4)
        surface.blit(shadow, shadow_rect)

    def _draw_vending(self, surface: pygame.Surface) -> None:
        if self.phase != Phase.HALLWAY:
            return
        pos = pygame.math.Vector2(self._map_size[0] - 3, 2.5)
        vx, vy = self._project_point(pos)
        box = pygame.Rect(0, 0, 36, 60)
        box.midbottom = (int(vx), int(vy))
        pygame.draw.rect(surface, (120, 98, 140), box, border_radius=8)
        slot = pygame.Rect(box.left + 6, box.centery, box.width - 12, 12)
        pygame.draw.rect(surface, (40, 30, 60), slot)
        label = self.small_font.render("€", COLORS.accent_fries)
        surface.blit(label, (box.centerx - label.get_width() // 2, box.top + 6))

    def _draw_npcs(self, surface: pygame.Surface) -> None:
        for npc in self.npcs:
            nx, ny = self._project_point(npc.position)
            rect = npc.sprite.get_rect()
            rect.midbottom = (int(nx), int(ny))
            surface.blit(npc.sprite, rect)
            if npc.ai_persona:
                label = self.small_font.render("AI", COLORS.accent_ui)
                surface.blit(label, (rect.centerx - label.get_width() // 2, rect.top - 14))

    def _draw_prompts(self, surface: pygame.Surface) -> None:
        lines: List[str] = []
        npc = self._nearby_npc()
        if npc:
            lines.append(f"Talk to {npc.name} — Enter")
        elif self.phase == Phase.HALLWAY and self._player_near_vending():
            lines.append("Open vending machine — Enter")
        phase_label = {
            Phase.EXTERIOR: "Outside Sprachschule (8:15–8:30)",
            Phase.HALLWAY: "Hallway scramble (8:30–8:35)",
            Phase.CLASS: "German class", 
        }[self.phase]
        lines.append(phase_label)
        panel = pygame.Surface((surface.get_width(), 120), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 0))
        y = 20
        for line in lines:
            text_surface = self.font.render(line, COLORS.text_light)
            shadow = self.font.render(line, COLORS.warm_dark)
            x = surface.get_width() // 2 - text_surface.get_width() // 2
            panel.blit(shadow, (x + 2, y + 2))
            panel.blit(text_surface, (x, y))
            y += 32
        surface.blit(panel, (0, surface.get_height() - 160))

    def _configure_world(self, map_size: tuple[int, int]) -> None:
        width, height = map_size
        max_x = max(0, width - 1)
        max_y = max(0, height - 1)
        corners = [
            iso_to_screen(0, 0, (0, 0)),
            iso_to_screen(max_x, 0, (0, 0)),
            iso_to_screen(0, max_y, (0, 0)),
            iso_to_screen(max_x, max_y, (0, 0)),
        ]
        min_x = min(x for x, _ in corners)
        max_x = max(x for x, _ in corners)
        min_y = min(y for _, y in corners)
        max_y = max(y for _, y in corners)
        margin_x = TILE_WIDTH * 3
        margin_y = TILE_HEIGHT * 5
        world_w = int(max_x - min_x + margin_x * 2)
        world_h = int(max_y - min_y + margin_y * 2)
        world_w = max(world_w, self.screen.get_width())
        world_h = max(world_h, self.screen.get_height())
        self.origin = (int(-min_x + margin_x), int(-min_y + margin_y))
        self.world_surface = pygame.Surface((world_w, world_h), pygame.SRCALPHA)
        self._background = pygame.Surface((world_w, world_h), pygame.SRCALPHA)
        self.camera_rect = pygame.Rect(0, 0, self.screen.get_width(), self.screen.get_height())

    def _project_point(self, position: pygame.math.Vector2) -> tuple[int, int]:
        return (
            int((position.x - position.y) * TILE_WIDTH // 2 + self.origin[0]),
            int((position.x + position.y) * TILE_HEIGHT // 2 + self.origin[1]),
        )

    def _project_tile(self, x: int, y: int) -> tuple[int, int]:
        return (
            int((x - y) * TILE_WIDTH // 2 + self.origin[0]),
            int((x + y) * TILE_HEIGHT // 2 + self.origin[1]),
        )

    def _camera_rect_view(self) -> pygame.Rect:
        px, py = self._project_point(self.player_pos)
        rect = pygame.Rect(0, 0, self.screen.get_width(), self.screen.get_height())
        rect.center = (int(px), int(py) - 60)
        rect.clamp_ip(self.world_surface.get_rect())
        self.camera_rect = rect
        return rect

    def _draw_self_talk(self, surface: pygame.Surface) -> None:
        if self.self_talk_duration <= 0:
            return
        px, py = self._project_point(self.player_pos)
        text = self.small_font.render(self.self_talk_message, COLORS.text_light)
        bubble = pygame.Surface((text.get_width() + 18, text.get_height() + 12), pygame.SRCALPHA)
        pygame.draw.rect(bubble, (246, 240, 228, 220), bubble.get_rect(), border_radius=8)
        bubble.blit(text, (9, 4))
        rect = bubble.get_rect()
        rect.midbottom = (px, py - self.player_sprite.get_height() + 6)
        surface.blit(bubble, rect)

    def _update_self_talk(self, dt: float) -> None:
        if self.self_talk_duration > 0:
            self.self_talk_duration -= dt
            if self.self_talk_duration <= 0:
                self.self_talk_message = ""
        self.self_talk_timer -= dt
        if self.self_talk_timer <= 0:
            phrases = [
                "im hungry",
                "what if i rp you rn?",
                "i hate people",
                "stupid classmates",
            ]
            self.self_talk_message = random.choice(phrases)
            self.self_talk_duration = 3.0
            self.self_talk_timer = random.uniform(32.0, 56.0)

    def _nearby_npc(self) -> Optional[SchoolNPC]:
        for npc in self.npcs:
            if self.player_pos.distance_to(npc.position) <= 1.1:
                return npc
        return None

    def _player_near_vending(self) -> bool:
        vending_pos = pygame.math.Vector2(self._map_size[0] - 3, 2.5)
        return self.player_pos.distance_to(vending_pos) <= 1.2

    def _interact_npc(self, npc: SchoolNPC) -> None:
        if npc.ai_persona:
            self.dialogue.open_ai(
                npc.name,
                npc.ai_persona,
                context_builder=lambda persona=npc.ai_persona: {
                    "day": str(self.state.day),
                    "mood": "high" if self.state.stats.mood > 60 else "low" if self.state.stats.mood < 35 else "neutral",
                    "friend": persona.split("_")[-1],
                },
            )
            friend_id = npc.ai_persona.split("_")[-1]
            self.state.relationships.adjust_friend(friend_id, 0.5)
            return
        if npc.lines:
            self.dialogue.open_info(npc.name, list(npc.lines))
        else:
            self.dialogue.open_info(npc.name, ["They wave awkwardly."])

    def _build_exterior_npcs(self) -> List[SchoolNPC]:
        sprites = self.classmate_sprites
        zara = SchoolNPC(
            name="Zara",
            position=pygame.math.Vector2(6.0, 7.5),
            sprite=sprites[0],
            ai_persona="friend_zara",
            roam=(pygame.math.Vector2(5.4, 7.2), pygame.math.Vector2(6.6, 8.0)),
            speed=0.35,
        )
        lukas = SchoolNPC(
            name="Lukas",
            position=pygame.math.Vector2(10.5, 8.5),
            sprite=sprites[1],
            ai_persona="friend_lukas",
        )
        passer = SchoolNPC(
            name="Passer-by",
            position=pygame.math.Vector2(11.0, 5.0),
            sprite=sprites[2],
            lines=("Morning! The teacher is in a good mood today.",),
            roam=(pygame.math.Vector2(10.0, 5.0), pygame.math.Vector2(12.0, 5.5)),
        )
        return [zara, lukas, passer]

    def _build_hallway_npcs(self) -> List[SchoolNPC]:
        sprites = self.classmate_sprites
        mina = SchoolNPC(
            name="Mina",
            position=pygame.math.Vector2(8.5, 2.5),
            sprite=sprites[2],
            ai_persona="friend_mina",
        )
        gossip = SchoolNPC(
            name="Gossip Crew",
            position=pygame.math.Vector2(14.0, 2.5),
            sprite=sprites[0],
            lines=("Did you finish the homework?", "I heard the quiz is harder."),
            roam=(pygame.math.Vector2(13.5, 2.5), pygame.math.Vector2(16.0, 2.5)),
        )
        quiet = SchoolNPC(
            name="Quiet Student",
            position=pygame.math.Vector2(4.0, 2.5),
            sprite=sprites[1],
            lines=("I like your notebook doodles.",),
        )
        return [mina, gossip, quiet]

    def _is_walkable(self, position: pygame.math.Vector2) -> bool:
        x, y = int(round(position.x)), int(round(position.y))
        width, height = self._map_size
        if not (0 <= x < width and 0 <= y < height):
            return False
        if (x, y) in self._walls:
            return False
        return True


__all__ = ["SchoolScene"]
