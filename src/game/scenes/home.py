"""Explorable home scene with door transitions and interactable rooms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import pygame

from game.ai.local_client import LocalAIClient
from game.config import COLORS, TILE_HEIGHT, TILE_WIDTH
from game.minigames.fry_minigame import FryMinigameController
from game.scenes.base import Scene
from game.state import GameState
from game.ui.fonts import PixelFont
from game.ui.phone import PhoneOverlay
from game.ui.pixel_art import nadiya_sprite


@dataclass
class Doorway:
    name: str
    position: pygame.math.Vector2
    target_room: str
    spawn: pygame.math.Vector2
    label: str


@dataclass
class HomeInteraction:
    name: str
    position: pygame.math.Vector2
    radius: float
    prompt: str
    action: str
    modes: Optional[Sequence[str]] = None


@dataclass
class HomeRoom:
    key: str
    display_name: str
    size: Tuple[int, int]
    floor_color: Tuple[int, int, int]
    accent_color: Tuple[int, int, int]
    blocked: set[Tuple[int, int]]
    doors: List[Doorway]
    interactions: List[HomeInteraction]


class HomeScene(Scene):
    """Allow the player to wander Nadiya's flat and trigger activities."""

    def __init__(
        self,
        state: GameState,
        screen: pygame.Surface,
        ai_client: LocalAIClient,
        *,
        mode: str,
    ) -> None:
        super().__init__(state)
        self.screen = screen
        self.ai_client = ai_client
        self.mode = mode
        self.font = PixelFont(base_size=11, scale=2)
        self.small_font = PixelFont(base_size=9, scale=2)
        self.player_sprite = nadiya_sprite()
        self.player_pos = pygame.math.Vector2(3.5, 3.5)
        self.player_speed = 3.2
        self.rooms = self._build_rooms()
        self.current_room = self.rooms["hall"]
        self.origin = (self.screen.get_width() // 2, 320)
        self._input: Dict[int, bool] = {}
        self.summary: List[str] = []
        self.minigame: FryMinigameController | None = None
        self._status_message = ""
        self._status_timer = 0.0
        self._room_fade = 0.0
        self._active_door: Optional[Doorway] = None
        self._active_interaction: Optional[HomeInteraction] = None
        self.phone = PhoneOverlay(state, ai_client, screen)

    def on_enter(self) -> None:
        if self.mode == "afternoon":
            self._set_status("Find the kitchen and rescue the fries.")
        elif self.mode == "evening":
            self._set_status("Check messages from the bedroom or wander a bit.")

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.minigame:
            self.minigame.handle_event(event)
            return
        if self.phone.active:
            self.phone.handle_event(event)
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_w, pygame.K_UP, pygame.K_s, pygame.K_DOWN, pygame.K_a, pygame.K_LEFT, pygame.K_d, pygame.K_RIGHT):
                self._input[event.key] = True
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self._active_door:
                    self._change_room(self._active_door)
                elif self._active_interaction:
                    self._trigger_interaction(self._active_interaction)
            elif event.key == pygame.K_p:
                if self.phone.active:
                    self.phone.close()
                else:
                    self.phone.open()
                    self.phone.active_app = "discord"
        elif event.type == pygame.KEYUP and event.key in self._input:
            self._input[event.key] = False

    def update(self, dt: float) -> None:
        if self.minigame:
            self.minigame.update(dt)
            if self.minigame.completed:
                if not self.summary:
                    self.summary.extend(self.minigame.summary)
                self.minigame = None
                self.completed = True
            return
        self.phone.update(dt)
        if self.phone.active:
            return
        self._update_player(dt)
        self._update_proximity()
        self._room_fade = max(0.0, self._room_fade - dt * 2.8)
        if self._status_timer > 0:
            self._status_timer -= dt
            if self._status_timer <= 0:
                self._status_message = ""
        if self.mode == "evening" and self.phone.completed and not self.completed:
            summary = self.phone.consume_summary()
            if summary:
                self.summary.extend(summary)
            if not self.summary:
                self.summary.append("Scrolled Discord until your brain untangled.")
            self.completed = True

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((20, 18, 28))
        self._draw_room(surface, self.current_room)
        self._draw_player(surface)
        self._draw_prompts(surface)
        if self._room_fade > 0:
            fade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            fade.fill((0, 0, 0, int(self._room_fade * 140)))
            surface.blit(fade, (0, 0))
        if self.phone.active:
            self.phone.render()
        if self.minigame:
            self.minigame.render()

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

    def _is_walkable(self, target: pygame.math.Vector2) -> bool:
        width, height = self.current_room.size
        if not (0.5 <= target.x <= width - 1.0 and 0.5 <= target.y <= height - 1.0):
            return False
        tile = (int(target.x), int(target.y))
        return tile not in self.current_room.blocked

    def _update_proximity(self) -> None:
        self._active_door = None
        self._active_interaction = None
        for door in self.current_room.doors:
            if self.player_pos.distance_to(door.position) <= 0.75:
                self._active_door = door
                break
        for interaction in self.current_room.interactions:
            if interaction.modes and self.mode not in interaction.modes:
                continue
            if self.player_pos.distance_to(interaction.position) <= interaction.radius:
                self._active_interaction = interaction
                break

    def _change_room(self, door: Doorway) -> None:
        target_room = self.rooms.get(door.target_room)
        if not target_room:
            return
        self.current_room = target_room
        self.player_pos = pygame.math.Vector2(door.spawn)
        self._room_fade = 1.0
        self._set_status(f"Entered {target_room.display_name}.")

    def _trigger_interaction(self, interaction: HomeInteraction) -> None:
        if interaction.modes and self.mode not in interaction.modes:
            return
        if interaction.action == "fryer" and self.mode == "afternoon" and not self.minigame:
            self._start_fry_minigame()
        elif interaction.action == "phone":
            self.phone.open()
            self.phone.active_app = "discord"
        else:
            self._set_status("Nothing interesting happens.")

    def _start_fry_minigame(self) -> None:
        self.minigame = FryMinigameController(self.state, self.screen)
        self._set_status("Fryer ignites — brace for oil.")

    def _draw_room(self, surface: pygame.Surface, room: HomeRoom) -> None:
        width, height = room.size
        for y in range(height):
            for x in range(width):
                cx = (x - y) * TILE_WIDTH // 2 + self.origin[0]
                cy = (x + y) * TILE_HEIGHT // 2 + self.origin[1]
                points = [
                    (cx, cy - TILE_HEIGHT // 2),
                    (cx + TILE_WIDTH // 2, cy),
                    (cx, cy + TILE_HEIGHT // 2),
                    (cx - TILE_WIDTH // 2, cy),
                ]
                color = room.floor_color
                if (x, y) in room.blocked:
                    color = room.accent_color
                pygame.draw.polygon(surface, color, points)
                pygame.draw.polygon(surface, COLORS.warm_dark, points, 1)
        for door in room.doors:
            self._draw_marker(surface, door.position, COLORS.accent_ui)
        for interaction in room.interactions:
            if interaction.modes and self.mode not in interaction.modes:
                continue
            self._draw_marker(surface, interaction.position, COLORS.accent_fries)

    def _draw_player(self, surface: pygame.Surface) -> None:
        px = (self.player_pos.x - self.player_pos.y) * TILE_WIDTH // 2 + self.origin[0]
        py = (self.player_pos.x + self.player_pos.y) * TILE_HEIGHT // 2 + self.origin[1]
        sprite = self.player_sprite
        rect = sprite.get_rect()
        rect.midbottom = (int(px), int(py))
        surface.blit(sprite, rect)
        shadow = pygame.Surface((sprite.get_width(), 8), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 110), shadow.get_rect())
        shadow_rect = shadow.get_rect()
        shadow_rect.midtop = (rect.centerx, rect.bottom - 4)
        surface.blit(shadow, shadow_rect)

    def _draw_marker(self, surface: pygame.Surface, position: pygame.math.Vector2, color: Tuple[int, int, int]) -> None:
        mx = (position.x - position.y) * TILE_WIDTH // 2 + self.origin[0]
        my = (position.x + position.y) * TILE_HEIGHT // 2 + self.origin[1]
        pygame.draw.circle(surface, color, (int(mx), int(my - 14)), 8)

    def _draw_prompts(self, surface: pygame.Surface) -> None:
        prompt_lines: List[str] = []
        if self._active_door:
            prompt_lines.append(f"Enter {self._active_door.label} — Press Enter")
        if self._active_interaction:
            prompt_lines.append(self._active_interaction.prompt)
        if self._status_message:
            prompt_lines.append(self._status_message)
        if not prompt_lines:
            return
        panel = pygame.Surface((surface.get_width(), 80), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 0))
        y = 12
        for line in prompt_lines:
            text_surface = self.font.render(line, COLORS.text_light)
            shadow = self.font.render(line, COLORS.warm_dark)
            x = surface.get_width() // 2 - text_surface.get_width() // 2
            panel.blit(shadow, (x + 2, y + 2))
            panel.blit(text_surface, (x, y))
            y += 28
        surface.blit(panel, (0, surface.get_height() - 140))

    def _set_status(self, text: str, duration: float = 2.2) -> None:
        self._status_message = text
        self._status_timer = duration

    def _build_rooms(self) -> Dict[str, HomeRoom]:
        rooms: Dict[str, HomeRoom] = {}
        hall_blocked = self._perimeter_blocks(7, 7)
        hall_blocked.update({(2, 3), (4, 3)})
        hall_doors = [
            Doorway("hall_to_kitchen", pygame.math.Vector2(5, 3), "kitchen", pygame.math.Vector2(1.5, 3.0), "Kitchen"),
            Doorway("hall_to_bedroom", pygame.math.Vector2(3, 1), "bedroom", pygame.math.Vector2(3.0, 4.5), "Bedroom"),
            Doorway("hall_to_living", pygame.math.Vector2(3, 5), "living", pygame.math.Vector2(3.0, 1.5), "Living Room"),
        ]
        rooms["hall"] = HomeRoom(
            key="hall",
            display_name="Hallway",
            size=(7, 7),
            floor_color=(92, 84, 110),
            accent_color=(62, 54, 78),
            blocked=hall_blocked,
            doors=hall_doors,
            interactions=[],
        )

        kitchen_blocked = self._perimeter_blocks(7, 6)
        kitchen_blocked.update({(x, 1) for x in range(1, 6)})
        kitchen_doors = [
            Doorway("kitchen_to_hall", pygame.math.Vector2(1, 3), "hall", pygame.math.Vector2(4.5, 3.0), "Hallway"),
        ]
        kitchen_interactions = [
            HomeInteraction(
                "fryer_station",
                pygame.math.Vector2(4.0, 2.0),
                0.9,
                "Press Enter to start the fry shift",
                "fryer",
                modes=("afternoon",),
            )
        ]
        rooms["kitchen"] = HomeRoom(
            key="kitchen",
            display_name="Kitchen",
            size=(7, 6),
            floor_color=(168, 144, 128),
            accent_color=(120, 96, 82),
            blocked=kitchen_blocked,
            doors=kitchen_doors,
            interactions=kitchen_interactions,
        )

        living_blocked = self._perimeter_blocks(7, 6)
        living_blocked.update({(2, 2), (4, 2)})
        living_doors = [
            Doorway("living_to_hall", pygame.math.Vector2(3, 1), "hall", pygame.math.Vector2(3.0, 4.5), "Hallway"),
        ]
        rooms["living"] = HomeRoom(
            key="living",
            display_name="Living Room",
            size=(7, 6),
            floor_color=(116, 88, 104),
            accent_color=(84, 60, 78),
            blocked=living_blocked,
            doors=living_doors,
            interactions=[],
        )

        bedroom_blocked = self._perimeter_blocks(7, 6)
        bedroom_blocked.update({(2, 2), (5, 3)})
        bedroom_doors = [
            Doorway("bedroom_to_hall", pygame.math.Vector2(3, 5), "hall", pygame.math.Vector2(3.0, 2.0), "Hallway"),
        ]
        bedroom_interactions = [
            HomeInteraction(
                "phone_desk",
                pygame.math.Vector2(5.0, 2.0),
                0.8,
                "Open phone — Press Enter",
                "phone",
                modes=("evening",),
            )
        ]
        rooms["bedroom"] = HomeRoom(
            key="bedroom",
            display_name="Bedroom",
            size=(7, 6),
            floor_color=(110, 100, 132),
            accent_color=(74, 68, 96),
            blocked=bedroom_blocked,
            doors=bedroom_doors,
            interactions=bedroom_interactions,
        )
        return rooms

    def _perimeter_blocks(self, width: int, height: int) -> set[Tuple[int, int]]:
        blocked: set[Tuple[int, int]] = set()
        for x in range(width):
            blocked.add((x, 0))
            blocked.add((x, height - 1))
        for y in range(height):
            blocked.add((0, y))
            blocked.add((width - 1, y))
        return blocked


__all__ = ["HomeScene"]
