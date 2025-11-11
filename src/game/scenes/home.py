"""Explorable home scene with door transitions and interactable rooms."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import random

import pygame

from game.ai.local_client import LocalAIClient
from game.balance import get_balance_section
from game.config import COLORS, TILE_HEIGHT, TILE_WIDTH
from game.minigames.fry_minigame import FryMinigameController
from game.scenes.base import Scene
from game.state import GameState
from game.scenes.isometric import iso_to_screen
from game.ui.dialogue_overlay import DialogueChoice, DialogueOverlay
from game.ui.fonts import PixelFont
from game.ui.phone import PhoneOverlay
from game.ui.pixel_art import (
    bed_sprite,
    cat_sprite,
    coffee_table_sprite,
    counter_sprite,
    desk_sprite,
    fridge_sprite,
    mom_sprite,
    nadiya_eat_sprite,
    nadiya_idle_sprite,
    nadiya_walk_cycle,
    neighbor_sprite,
    plant_sprite,
    shower_sprite,
    sink_sprite,
    sofa_sprite,
    stove_sprite,
    tv_stand_sprite,
    wardrobe_sprite,
)


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
class HomeDecor:
    sprite: pygame.Surface
    position: pygame.math.Vector2
    anchor: str = "midbottom"
    pixel_offset: pygame.math.Vector2 = field(default_factory=lambda: pygame.math.Vector2(0, 0))


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
    decor: List[HomeDecor]


@dataclass
class HomeNPC:
    name: str
    room: str
    position: pygame.math.Vector2
    sprite: pygame.Surface
    ai_persona: Optional[str] = None
    dialog_lines: Tuple[str, ...] = ()
    patrol: Tuple[pygame.math.Vector2, pygame.math.Vector2] | None = None
    speed: float = 0.6
    direction: int = 1


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
        self.idle_sprite = nadiya_idle_sprite()
        self.walk_cycle = list(nadiya_walk_cycle())
        self.eat_sprite = nadiya_eat_sprite()
        self.player_sprite = self.idle_sprite
        self.walk_timer = 0.0
        self.walk_frame = 0
        self.is_moving = False
        self.eat_timer = 0.0
        self.snack_cooldown = 0.0
        self.mom_sprite = mom_sprite()
        self.player_pos = pygame.math.Vector2(3.5, 3.5)
        self.player_speed = 3.2
        self.rooms = self._build_rooms()
        self.current_room = self.rooms["hall"]
        if mode == "dawn":
            self.current_room = self.rooms["bedroom"]
            self.player_pos = pygame.math.Vector2(3.0, 4.2)
        elif mode == "evening":
            self.current_room = self.rooms["bedroom"]
            self.player_pos = pygame.math.Vector2(4.0, 2.2)
        self.origin = (0, 0)
        self._world_surface = pygame.Surface((self.screen.get_width(), self.screen.get_height()))
        self._camera_rect = pygame.Rect(0, 0, self.screen.get_width(), self.screen.get_height())
        self._input: Dict[int, bool] = {}
        self.summary: List[str] = []
        self.minigame: FryMinigameController | None = None
        self._status_message = ""
        self._status_timer = 0.0
        self._room_fade = 0.0
        self._active_door: Optional[Doorway] = None
        self._active_interaction: Optional[HomeInteraction] = None
        self.phone = PhoneOverlay(state, ai_client, screen)
        self.dialogue = DialogueOverlay(state, ai_client, screen)
        self.npcs: List[HomeNPC] = self._build_npcs(mode)
        self._active_npc: Optional[HomeNPC] = None
        self.morning_tasks = {"shower": False, "outfit": False, "pack": False}
        self.self_talk_timer = random.uniform(24.0, 48.0)
        self.self_talk_duration = 0.0
        self.self_talk_message = ""
        self._configure_world(self.current_room)

    def on_enter(self) -> None:
        if self.mode == "dawn":
            self._set_status("06:40 — shower, clothes, bag, then head out.", duration=4.0)
        if self.mode == "afternoon":
            self._set_status("Find the kitchen and rescue the fries.")
        elif self.mode == "evening":
            self._set_status("Check messages from the bedroom or wander a bit.")

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.minigame:
            self.minigame.handle_event(event)
            return
        if self.dialogue.active:
            self.dialogue.handle_event(event)
            return
        if self.phone.active:
            self.phone.handle_event(event)
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_w, pygame.K_UP, pygame.K_s, pygame.K_DOWN, pygame.K_a, pygame.K_LEFT, pygame.K_d, pygame.K_RIGHT):
                self._input[event.key] = True
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self._active_npc:
                    self._trigger_npc(self._active_npc)
                elif self._active_door:
                    self._change_room(self._active_door)
                elif self._active_interaction:
                    self._trigger_interaction(self._active_interaction)
        elif event.type == pygame.KEYUP and event.key in self._input:
            self._input[event.key] = False

    def update(self, dt: float) -> None:
        if self.minigame:
            self.is_moving = False
            self.minigame.update(dt)
            if self.minigame.completed:
                if not self.summary:
                    self.summary.extend(self.minigame.summary)
                self.minigame = None
                self.completed = True
            return
        self.dialogue.update(dt)
        if not self.dialogue.active:
            new_lines = self.dialogue.consume_summary()
            if new_lines:
                self.summary.extend(new_lines)
        if self.dialogue.active:
            self.is_moving = False
            return
        self.phone.update(dt)
        if self.phone.active:
            self.is_moving = False
            return
        self.is_moving = self._update_player(dt)
        if self.eat_timer > 0:
            self.eat_timer = max(0.0, self.eat_timer - dt)
        if self.snack_cooldown > 0:
            self.snack_cooldown = max(0.0, self.snack_cooldown - dt)
        self._update_proximity()
        self._update_npcs(dt)
        self._update_self_talk(dt)
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
        self._world_surface.fill((20, 18, 28))
        self._draw_room(self._world_surface, self.current_room)
        self._draw_highlights(self._world_surface)
        self._draw_npcs(self._world_surface)
        self._draw_player(self._world_surface)
        self._draw_self_talk(self._world_surface)
        camera = self._camera_rect_view()
        surface.blit(self._world_surface, (0, 0), camera)
        self._draw_prompts(surface)
        if self._room_fade > 0:
            fade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            fade.fill((0, 0, 0, int(self._room_fade * 140)))
            surface.blit(fade, (0, 0))
        if self.dialogue.active:
            self.dialogue.render()
        if self.phone.active:
            self.phone.render()
        if self.minigame:
            self.minigame.render()

    def get_objectives(self) -> list[str]:
        lines: list[str] = []
        if self.mode == "dawn":
            mapping = [
                ("shower", "Take a shower in the bathroom"),
                ("outfit", "Change clothes at the wardrobe"),
                ("pack", "Grab the bag from the bedroom desk"),
            ]
            for key, label in mapping:
                mark = "✔" if self.morning_tasks.get(key) else "□"
                lines.append(f"{mark} {label}")
            lines.append("Press Enter at the front door once you are ready to leave.")
        elif self.mode == "afternoon":
            lines.append("Head to the kitchen and start the fryer (Enter).")
            lines.append("Use snacks or the fridge to recover if hunger is low.")
            lines.append("Talk to Mom if she's nearby for optional dialogue.")
        elif self.mode == "evening":
            lines.append("Open the phone with P to chat on Discord.")
            lines.append("Wander the flat for extra flavour conversations.")
            lines.append("When you're done, interact with the bed to rest.")
        return lines

    def _update_player(self, dt: float) -> bool:
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
            self.walk_timer = 0.0
            self.walk_frame = 0
            return False
        direction = direction.normalize()
        speed = self.player_speed * self.state.fatigue_modifier()
        target = self.player_pos + direction * speed * dt
        if self._is_walkable(target):
            self.player_pos = target
            self._camera_rect_view()
            self.walk_timer += dt
            if self.walk_timer >= 0.12:
                self.walk_frame = (self.walk_frame + 1) % max(1, len(self.walk_cycle))
                self.walk_timer = 0.0
            return True
        self.walk_timer = 0.0
        self.walk_frame = 0
        return False

    def _is_walkable(self, target: pygame.math.Vector2) -> bool:
        width, height = self.current_room.size
        if not (0.5 <= target.x <= width - 1.0 and 0.5 <= target.y <= height - 1.0):
            return False
        tile = (int(target.x), int(target.y))
        return tile not in self.current_room.blocked

    def _update_proximity(self) -> None:
        self._active_door = None
        self._active_interaction = None
        self._active_npc = None
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
        for npc in self.npcs:
            if npc.room != self.current_room.key:
                continue
            if self.player_pos.distance_to(npc.position) <= 1.0:
                self._active_npc = npc
                break

    def _change_room(self, door: Doorway) -> None:
        target_room = self.rooms.get(door.target_room)
        if not target_room:
            return
        self.current_room = target_room
        self.player_pos = pygame.math.Vector2(door.spawn)
        self._room_fade = 1.0
        self._set_status(f"Entered {target_room.display_name}.")
        self._configure_world(target_room)

    def _update_npcs(self, dt: float) -> None:
        for npc in self.npcs:
            if not npc.patrol:
                continue
            start, end = npc.patrol
            target = end if npc.direction > 0 else start
            direction_vec = target - npc.position
            if direction_vec.length_squared() < 0.05:
                npc.direction *= -1
                continue
            move = direction_vec.normalize() * npc.speed * dt
            npc.position += move

    def _trigger_interaction(self, interaction: HomeInteraction) -> None:
        if interaction.modes and self.mode not in interaction.modes:
            return
        if interaction.action == "fryer" and self.mode == "afternoon" and not self.minigame:
            self._start_fry_minigame()
        elif interaction.action == "phone":
            self.phone.open()
            self.phone.active_app = "discord"
        elif interaction.action == "shower" and self.mode == "dawn":
            if not self.morning_tasks["shower"]:
                self.morning_tasks["shower"] = True
                bonus = get_balance_section("segments").get("dawn", {}).get("energy_bonus_shower", 4)
                self.state.stats.apply_energy(float(bonus))
                self._set_status("Hot shower achieved.")
                self.summary.append("Took a too-fast shower.")
            else:
                self._set_status("Already showered.")
        elif interaction.action == "outfit" and self.mode == "dawn":
            if not self.morning_tasks["outfit"]:
                self.morning_tasks["outfit"] = True
                self._set_status("Outfit picked: chaotic cozy.")
                self.summary.append("Pulled an outfit together.")
            else:
                self._set_status("Wardrobe already raided.")
        elif interaction.action == "pack" and self.mode == "dawn":
            if not self.morning_tasks["pack"]:
                self.morning_tasks["pack"] = True
                self._set_status("Bag packed with questionable priorities.")
                self.summary.append("Stuffed essentials into the backpack.")
            else:
                self._set_status("Bag is already packed.")
        elif interaction.action == "snack":
            if self.snack_cooldown > 0:
                self._set_status("Give it a moment before raiding the counter again.")
                return
            home_cfg = get_balance_section("home")
            hunger_gain = float(home_cfg.get("snack_hunger", 6))
            mood_gain = float(home_cfg.get("snack_mood", 1))
            cooldown = float(home_cfg.get("snack_cooldown", 18))
            self.state.stats.apply_hunger(hunger_gain)
            if mood_gain:
                self.state.stats.apply_mood(mood_gain)
            self.eat_timer = 1.6
            self.snack_cooldown = cooldown
            self._set_status("Counter snack inhaled.")
            self.summary.append("Snagged a counter snack to stay upright.")
        elif interaction.action == "exit" and self.mode == "dawn":
            if all(self.morning_tasks.values()):
                mood_bonus = get_balance_section("segments").get("dawn", {}).get("mood_bonus_ready", 2)
                self.state.stats.apply_mood(float(mood_bonus))
                self.summary.append("Ready for school despite the morning chaos.")
                self.completed = True
            else:
                todo = [
                    label
                    for key, label in (
                        ("shower", "shower"),
                        ("outfit", "get dressed"),
                        ("pack", "pack bag"),
                    )
                    if not self.morning_tasks[key]
                ]
                self._set_status("Still need to " + ", ".join(todo) + ".", duration=3.0)
        else:
            self._set_status("Nothing interesting happens.")

    def _trigger_npc(self, npc: HomeNPC) -> None:
        if npc.ai_persona:
            self.dialogue.open_ai(
                npc.name,
                npc.ai_persona,
                context_builder=lambda: {
                    "mood": "high" if self.state.stats.mood > 60 else "low" if self.state.stats.mood < 35 else "neutral",
                    "relationship": str(int(self.state.relationships.mom)),
                    "energy": str(int(self.state.stats.energy)),
                },
            )
        elif npc.dialog_lines:
            self.dialogue.open_info(npc.name, list(npc.dialog_lines))
        else:
            self.dialogue.open_info(npc.name, ["They nod politely but stay quiet."])

    def _start_fry_minigame(self) -> None:
        self.minigame = FryMinigameController(self.state, self.screen)
        self._set_status("Fryer ignites — brace for oil.")

    def _draw_room(self, surface: pygame.Surface, room: HomeRoom) -> None:
        width, height = room.size
        for y in range(height):
            for x in range(width):
                cx, cy = self._project_tile(x, y)
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
        self._draw_decor(surface, room)

    def _draw_player(self, surface: pygame.Surface) -> None:
        px, py = self._project_point(self.player_pos)
        if self.eat_timer > 0:
            sprite = self.eat_sprite
        elif self.is_moving and self.walk_cycle:
            sprite = self.walk_cycle[self.walk_frame % len(self.walk_cycle)]
        else:
            sprite = self.idle_sprite
        self.player_sprite = sprite
        rect = sprite.get_rect()
        rect.midbottom = (int(px), int(py))
        surface.blit(sprite, rect)
        shadow = pygame.Surface((sprite.get_width(), 8), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 110), shadow.get_rect())
        shadow_rect = shadow.get_rect()
        shadow_rect.midtop = (rect.centerx, rect.bottom - 4)
        surface.blit(shadow, shadow_rect)

    def _draw_decor(self, surface: pygame.Surface, room: HomeRoom) -> None:
        items = sorted(room.decor, key=lambda item: item.position.y)
        for decor in items:
            dx, dy = self._project_point(decor.position)
            rect = decor.sprite.get_rect()
            if decor.anchor == "center":
                rect.center = (int(dx + decor.pixel_offset.x), int(dy + decor.pixel_offset.y))
            elif decor.anchor == "topleft":
                rect.topleft = (int(dx + decor.pixel_offset.x), int(dy + decor.pixel_offset.y))
            else:
                rect.midbottom = (int(dx + decor.pixel_offset.x), int(dy + decor.pixel_offset.y))
            surface.blit(decor.sprite, rect)

    def _draw_npcs(self, surface: pygame.Surface) -> None:
        for npc in self.npcs:
            if npc.room != self.current_room.key:
                continue
            nx, ny = self._project_point(npc.position)
            rect = npc.sprite.get_rect()
            rect.midbottom = (int(nx), int(ny))
            surface.blit(npc.sprite, rect)
            shadow = pygame.Surface((npc.sprite.get_width(), 6), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 90), shadow.get_rect())
            shadow_rect = shadow.get_rect()
            shadow_rect.midtop = (rect.centerx, rect.bottom - 4)
            surface.blit(shadow, shadow_rect)

    def _draw_marker(self, surface: pygame.Surface, position: pygame.math.Vector2, color: Tuple[int, int, int]) -> None:
        mx, my = self._project_point(position)
        diamond = [
            (int(mx), int(my - 12)),
            (int(mx + 12), int(my)),
            (int(mx), int(my + 12)),
            (int(mx - 12), int(my)),
        ]
        glow = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.polygon(glow, (*color, 90), [
            (16, 4),
            (28, 16),
            (16, 28),
            (4, 16),
        ])
        glow_rect = glow.get_rect()
        glow_rect.center = (int(mx), int(my))
        surface.blit(glow, glow_rect)
        pygame.draw.polygon(surface, color, diamond, 2)

    def _draw_highlights(self, surface: pygame.Surface) -> None:
        if self._active_door:
            self._draw_marker(surface, self._active_door.position, COLORS.accent_ui)
        if self._active_interaction:
            self._draw_marker(surface, self._active_interaction.position, COLORS.accent_fries)
        if self._active_npc:
            self._draw_marker(surface, self._active_npc.position, COLORS.accent_cool)

    def _draw_prompts(self, surface: pygame.Surface) -> None:
        prompt_lines: List[str] = []
        if self._active_door:
            prompt_lines.append(f"Enter {self._active_door.label} — Press Enter")
        if self._active_interaction:
            prompt_lines.append(self._active_interaction.prompt)
        if self._active_npc:
            prompt_lines.append(f"Talk to {self._active_npc.name} — Press Enter")
        if self._status_message:
            prompt_lines.append(self._status_message)
        if not prompt_lines:
            return
        panel = pygame.Surface((surface.get_width(), 108), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 0))
        y = 12
        for line in prompt_lines:
            text_surface = self.font.render(line, COLORS.text_light)
            shadow = self.font.render(line, COLORS.warm_dark)
            x = surface.get_width() // 2 - text_surface.get_width() // 2
            panel.blit(shadow, (x + 2, y + 2))
            panel.blit(text_surface, (x, y))
            y += 28
        if self.mode == "dawn":
            checklist = ", ".join(
                ("✔" if self.morning_tasks[key] else "□") + " " + label
                for key, label in (
                    ("shower", "shower"),
                    ("outfit", "get dressed"),
                    ("pack", "pack bag"),
                )
            )
            status_text = self.small_font.render("Morning tasks: " + checklist, COLORS.text_light)
            panel.blit(status_text, (surface.get_width() // 2 - status_text.get_width() // 2, y))
        surface.blit(panel, (0, surface.get_height() - 160))

    def _set_status(self, text: str, duration: float = 2.2) -> None:
        self._status_message = text
        self._status_timer = duration

    def _build_rooms(self) -> Dict[str, HomeRoom]:
        rooms: Dict[str, HomeRoom] = {}

        hall_blocked = self._perimeter_blocks(7, 7)
        hall_blocked.update({(2, 3), (4, 3), (1, 5), (2, 5), (5, 2)})
        hall_doors = [
            Doorway("hall_to_kitchen", pygame.math.Vector2(5, 3), "kitchen", pygame.math.Vector2(1.5, 3.0), "Kitchen"),
            Doorway("hall_to_bedroom", pygame.math.Vector2(3, 1), "bedroom", pygame.math.Vector2(3.0, 4.5), "Bedroom"),
            Doorway("hall_to_living", pygame.math.Vector2(3, 5), "living", pygame.math.Vector2(3.0, 1.5), "Living Room"),
            Doorway("hall_to_bathroom", pygame.math.Vector2(1, 5), "bathroom", pygame.math.Vector2(3.0, 1.5), "Bathroom"),
        ]
        hall_interactions = [
            HomeInteraction(
                "exit_door",
                pygame.math.Vector2(6.0, 3.0),
                0.9,
                "Leave for school — Press Enter",
                "exit",
                modes=("dawn",),
            )
        ]
        hall_decor = [
            HomeDecor(wardrobe_sprite(), pygame.math.Vector2(2.2, 5.8)),
            HomeDecor(plant_sprite(), pygame.math.Vector2(5.0, 2.3), pixel_offset=pygame.math.Vector2(0, -12)),
        ]
        rooms["hall"] = HomeRoom(
            key="hall",
            display_name="Hallway",
            size=(7, 7),
            floor_color=(92, 84, 110),
            accent_color=(62, 54, 78),
            blocked=hall_blocked,
            doors=hall_doors,
            interactions=hall_interactions,
            decor=hall_decor,
        )

        kitchen_blocked = self._perimeter_blocks(7, 6)
        kitchen_blocked.update({(x, 1) for x in range(1, 6)})
        kitchen_blocked.update({(5, 2), (5, 3)})
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
            ),
            HomeInteraction(
                "snack_counter",
                pygame.math.Vector2(3.2, 3.4),
                0.8,
                "Grab a quick bite — Press Enter",
                "snack",
                modes=("dawn", "afternoon", "evening"),
            ),
        ]
        kitchen_decor = [
            HomeDecor(counter_sprite(), pygame.math.Vector2(3.6, 1.2)),
            HomeDecor(stove_sprite(), pygame.math.Vector2(2.2, 1.3)),
            HomeDecor(fridge_sprite(), pygame.math.Vector2(5.6, 1.0)),
            HomeDecor(coffee_table_sprite(), pygame.math.Vector2(3.2, 3.6)),
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
            decor=kitchen_decor,
        )

        living_blocked = self._perimeter_blocks(7, 6)
        living_blocked.update({(2, 2), (3, 2), (4, 2), (2, 3), (4, 3)})
        living_doors = [
            Doorway("living_to_hall", pygame.math.Vector2(3, 1), "hall", pygame.math.Vector2(3.0, 4.5), "Hallway"),
        ]
        living_decor = [
            HomeDecor(sofa_sprite(), pygame.math.Vector2(3.2, 3.6)),
            HomeDecor(coffee_table_sprite(), pygame.math.Vector2(3.2, 4.6)),
            HomeDecor(tv_stand_sprite(), pygame.math.Vector2(3.2, 1.4)),
            HomeDecor(plant_sprite(), pygame.math.Vector2(5.4, 2.0), pixel_offset=pygame.math.Vector2(0, -14)),
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
            decor=living_decor,
        )

        bedroom_blocked = self._perimeter_blocks(7, 6)
        bedroom_blocked.update({(1, 3), (1, 4), (2, 3), (2, 4), (5, 2), (5, 3)})
        bedroom_doors = [
            Doorway("bedroom_to_hall", pygame.math.Vector2(3, 5), "hall", pygame.math.Vector2(3.0, 2.0), "Hallway"),
        ]
        bedroom_interactions = [
            HomeInteraction(
                "outfit_closet",
                pygame.math.Vector2(1.8, 2.2),
                0.9,
                "Pick outfit — Press Enter",
                "outfit",
                modes=("dawn",),
            ),
            HomeInteraction(
                "pack_bag",
                pygame.math.Vector2(5.4, 3.4),
                0.9,
                "Pack bag — Press Enter",
                "pack",
                modes=("dawn",),
            ),
            HomeInteraction(
                "phone_desk",
                pygame.math.Vector2(5.2, 2.2),
                0.8,
                "Open phone — Press Enter",
                "phone",
                modes=("evening",),
            ),
        ]
        bedroom_decor = [
            HomeDecor(bed_sprite(), pygame.math.Vector2(2.4, 4.2)),
            HomeDecor(wardrobe_sprite(), pygame.math.Vector2(1.6, 2.0)),
            HomeDecor(desk_sprite(), pygame.math.Vector2(5.2, 2.0)),
            HomeDecor(plant_sprite(), pygame.math.Vector2(4.6, 3.0), pixel_offset=pygame.math.Vector2(0, -12)),
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
            decor=bedroom_decor,
        )

        bathroom_blocked = self._perimeter_blocks(5, 5)
        bathroom_blocked.update({(1, 2), (3, 2), (1, 3), (3, 3)})
        bathroom_doors = [
            Doorway("bathroom_to_hall", pygame.math.Vector2(3, 4), "hall", pygame.math.Vector2(1.5, 4.5), "Hallway"),
        ]
        bathroom_interactions = [
            HomeInteraction(
                "shower_booth",
                pygame.math.Vector2(3.0, 2.2),
                0.8,
                "Quick shower — Press Enter",
                "shower",
                modes=("dawn",),
            )
        ]
        bathroom_decor = [
            HomeDecor(shower_sprite(), pygame.math.Vector2(3.0, 2.0)),
            HomeDecor(sink_sprite(), pygame.math.Vector2(2.0, 3.2)),
        ]
        rooms["bathroom"] = HomeRoom(
            key="bathroom",
            display_name="Bathroom",
            size=(5, 5),
            floor_color=(120, 150, 168),
            accent_color=(88, 120, 138),
            blocked=bathroom_blocked,
            doors=bathroom_doors,
            interactions=bathroom_interactions,
            decor=bathroom_decor,
        )
        return rooms

    def toggle_phone(self) -> None:
        if self.mode == "dawn" and not self.phone.active:
            self._set_status("No doomscrolling before class.", duration=2.5)
            return
        if self.phone.active:
            self.phone.close()
        else:
            self.phone.open()
            self.phone.active_app = "discord"

    def _build_npcs(self, mode: str) -> List[HomeNPC]:
        mom = HomeNPC(
            name="Mom",
            room="living" if mode != "dawn" else "kitchen",
            position=pygame.math.Vector2(3.0, 3.0) if mode != "dawn" else pygame.math.Vector2(3.4, 2.4),
            sprite=self.mom_sprite,
            ai_persona="mom",
            patrol=(pygame.math.Vector2(2.4, 3.0), pygame.math.Vector2(4.6, 3.2)),
            speed=0.5,
        )
        neighbor = HomeNPC(
            name="Neighbor Vesna",
            room="hall",
            position=pygame.math.Vector2(2.2, 2.5),
            sprite=neighbor_sprite(),
            dialog_lines=("She's humming an old tune.", "'Need anything, Nadiya?'"),
        )
        cat = HomeNPC(
            name="Apartment Cat",
            room="bedroom",
            position=pygame.math.Vector2(4.0, 3.5),
            sprite=cat_sprite(),
            dialog_lines=("It blinks slowly at you.", "Maybe it's secretly judging."),
        )
        return [mom, neighbor, cat]

    def _perimeter_blocks(self, width: int, height: int) -> set[Tuple[int, int]]:
        blocked: set[Tuple[int, int]] = set()
        for x in range(width):
            blocked.add((x, 0))
            blocked.add((x, height - 1))
        for y in range(height):
            blocked.add((0, y))
            blocked.add((width - 1, y))
        return blocked

    def _configure_world(self, room: HomeRoom) -> None:
        width, height = room.size
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
        margin_x = TILE_WIDTH * 2
        margin_y = TILE_HEIGHT * 4
        width = int(max_x - min_x + margin_x * 2)
        height = int(max_y - min_y + margin_y * 2)
        width = max(width, self.screen.get_width())
        height = max(height, self.screen.get_height())
        self.origin = (int(-min_x + margin_x), int(-min_y + margin_y))
        self._world_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self._camera_rect = pygame.Rect(0, 0, self.screen.get_width(), self.screen.get_height())

    def _project_point(self, position: pygame.math.Vector2) -> Tuple[int, int]:
        return (
            int((position.x - position.y) * TILE_WIDTH // 2 + self.origin[0]),
            int((position.x + position.y) * TILE_HEIGHT // 2 + self.origin[1]),
        )

    def _project_tile(self, x: int, y: int) -> Tuple[int, int]:
        return (
            int((x - y) * TILE_WIDTH // 2 + self.origin[0]),
            int((x + y) * TILE_HEIGHT // 2 + self.origin[1]),
        )

    def _camera_rect_view(self) -> pygame.Rect:
        px, py = self._project_point(self.player_pos)
        rect = pygame.Rect(0, 0, self.screen.get_width(), self.screen.get_height())
        rect.center = (int(px), int(py) - 40)
        rect.clamp_ip(self._world_surface.get_rect())
        self._camera_rect = rect
        return rect

    def _draw_self_talk(self, surface: pygame.Surface) -> None:
        if self.self_talk_duration <= 0:
            return
        px, py = self._project_point(self.player_pos)
        text = self.small_font.render(self.self_talk_message, COLORS.text_light)
        bubble = pygame.Surface((text.get_width() + 18, text.get_height() + 12), pygame.SRCALPHA)
        pygame.draw.rect(bubble, (248, 240, 220, 220), bubble.get_rect(), border_radius=8)
        bubble.blit(text, (9, 4))
        rect = bubble.get_rect()
        rect.midbottom = (px, py - self.player_sprite.get_height() + 8)
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
            self.self_talk_duration = 3.2
            self.self_talk_timer = random.uniform(26.0, 48.0)


__all__ = ["HomeScene"]

