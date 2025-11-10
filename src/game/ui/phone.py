"""In-game phone overlay with a Discord-like chat app and utilities."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional, Sequence, Tuple

import pygame

from game.ai.local_client import AIRequest, LocalAIClient
from game.balance import get_balance_section
from game.config import COLORS
from game.state import GameState
from game.ui.fonts import PixelFont


@dataclass
class ChatMessage:
    speaker: str
    text: str


@dataclass
class Conversation:
    friend_id: str
    display_name: str
    avatar: pygame.Surface
    color: Tuple[int, int, int]
    messages: Deque[ChatMessage]
    pending_request: Optional[int] = None


class DiscordApp:
    """Discord inspired chat application living inside the phone overlay."""

    def __init__(
        self,
        state: GameState,
        ai_client: LocalAIClient,
        *,
        fonts: dict[str, PixelFont],
        panel_size: Tuple[int, int],
    ) -> None:
        self.state = state
        self.ai_client = ai_client
        self.font = fonts["body"]
        self.small_font = fonts["small"]
        self.title_font = fonts["title"]
        self.panel_width, self.panel_height = panel_size
        self.friends: Sequence[Tuple[str, str, Tuple[int, int, int]]] = (
            ("zara", "Zara", (255, 132, 124)),
            ("lukas", "Lukas", (120, 184, 226)),
            ("mina", "Mina", (154, 214, 146)),
        )
        self.conversations: Dict[str, Conversation] = {}
        self.current_index = 0
        self.input_buffer: List[str] = []
        self.cursor_timer = 0.0
        self.cursor_visible = True
        self.request_close = False
        self.summary: List[str] = []
        self.session_timer = float(
            get_balance_section("segments").get("evening", {}).get("base_timer", 40.0)
        )
        self.session_finished = False
        self._evening_cfg = get_balance_section("segments").get("evening", {})
        self._event_cfg = get_balance_section("events")
        self._initialise_conversations()

    def _initialise_conversations(self) -> None:
        greetings = {
            "zara": "Zara: i heard you survived the hallway raid?", 
            "lukas": "Lukas: report in, did the fries bite back?",
            "mina": "Mina: hey love, breathing exercises after class?",
        }
        for friend_id, display_name, color in self.friends:
            avatar = self._build_avatar(display_name[0], color)
            convo = Conversation(
                friend_id=friend_id,
                display_name=display_name,
                avatar=avatar,
                color=color,
                messages=deque(maxlen=24),
            )
            convo.messages.append(ChatMessage(display_name, greetings.get(friend_id, "Hey hey!")))
            self.conversations[friend_id] = convo

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.session_finished:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.request_close = True
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.request_close = True
            elif event.key in (pygame.K_TAB, pygame.K_q):
                self._cycle_friend(-1)
            elif event.key in (pygame.K_e,):
                self._cycle_friend(1)
            elif event.key == pygame.K_LEFT:
                self._cycle_friend(-1)
            elif event.key == pygame.K_RIGHT:
                self._cycle_friend(1)
            elif event.key == pygame.K_RETURN:
                text = "".join(self.input_buffer).strip()
                if text:
                    self._send_message(text)
                    self.input_buffer.clear()
            elif event.key == pygame.K_BACKSPACE:
                if self.input_buffer:
                    self.input_buffer.pop()
            else:
                if event.unicode and event.unicode.isprintable():
                    self.input_buffer.append(event.unicode)

    def update(self, dt: float, *, active: bool) -> None:
        if self.session_finished:
            return
        drain_rate = 1.0 if active else 0.35
        self.session_timer -= dt * drain_rate
        if self.session_timer <= 0 and not self.session_finished:
            self.session_finished = True
            if not self.summary:
                self.summary.append("No chaotic pings tonight, just quiet scrolling.")
            return
        self.cursor_timer += dt
        if self.cursor_timer >= 0.45:
            self.cursor_visible = not self.cursor_visible
            self.cursor_timer = 0.0

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((28, 26, 40, 240))
        friend_id, display_name, _ = self.friends[self.current_index]
        header = self.title_font.render(display_name, COLORS.text_light)
        surface.blit(header, (20, 16))
        timer_surface = self.small_font.render(
            f"{int(max(0, self.session_timer)):02d}s", COLORS.accent_fries
        )
        surface.blit(timer_surface, (surface.get_width() - timer_surface.get_width() - 20, 20))
        self._render_friend_tabs(surface)
        chat_rect = pygame.Rect(20, 80, surface.get_width() - 40, surface.get_height() - 180)
        self._render_messages(surface, chat_rect, self.conversations[friend_id])
        self._render_input(surface)
        hint = self.small_font.render("Enter to send • Q/E or ←/→ to switch friend", COLORS.text_light)
        surface.blit(hint, (24, surface.get_height() - 44))
        if self.session_finished:
            wrap = self.small_font.render("Session wrapped — press Esc", COLORS.accent_ui)
            surface.blit(wrap, (24, surface.get_height() - 64))

    def _render_friend_tabs(self, surface: pygame.Surface) -> None:
        base_x = 20
        for idx, (friend_id, display_name, color) in enumerate(self.friends):
            convo = self.conversations[friend_id]
            tab_rect = pygame.Rect(base_x + idx * 90, 56, 80, 28)
            tab_surface = pygame.Surface(tab_rect.size, pygame.SRCALPHA)
            active = idx == self.current_index
            tab_color = (*color, 200) if active else (44, 40, 60, 200)
            tab_surface.fill(tab_color)
            label = self.small_font.render(display_name, COLORS.text_light)
            tab_surface.blit(label, (8, 6))
            surface.blit(tab_surface, tab_rect)
            if convo.pending_request is not None and not active:
                dot = self.small_font.render("•", COLORS.accent_fries)
                surface.blit(dot, (tab_rect.right - 12, tab_rect.top + 4))

    def _render_messages(self, surface: pygame.Surface, rect: pygame.Rect, convo: Conversation) -> None:
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        panel.fill((18, 16, 28, 220))
        y = panel.get_height() - 18
        for message in reversed(convo.messages):
            text_surface = self.font.render(message.text, COLORS.text_light)
            bubble_width = text_surface.get_width() + 20
            bubble_height = text_surface.get_height() + 12
            if message.speaker == "Nadiya":
                bubble_rect = pygame.Rect(panel.get_width() - bubble_width - 8, y - bubble_height, bubble_width, bubble_height)
                bubble_color = (74, 52, 98, 220)
            else:
                bubble_rect = pygame.Rect(8, y - bubble_height, bubble_width, bubble_height)
                bubble_color = (46, 40, 62, 220)
            bubble = pygame.Surface(bubble_rect.size, pygame.SRCALPHA)
            bubble.fill(bubble_color)
            bubble.blit(text_surface, (10, 6))
            panel.blit(bubble, bubble_rect)
            if message.speaker != "Nadiya":
                avatar = convo.avatar
                panel.blit(avatar, (bubble_rect.left - avatar.get_width() - 6, bubble_rect.top + 2))
            y -= bubble_height + 10
            if y < 32:
                break
        surface.blit(panel, rect.topleft)

    def _render_input(self, surface: pygame.Surface) -> None:
        input_rect = pygame.Rect(20, surface.get_height() - 100, surface.get_width() - 40, 60)
        panel = pygame.Surface(input_rect.size, pygame.SRCALPHA)
        panel.fill((24, 20, 32, 220))
        text = "".join(self.input_buffer)
        if self.cursor_visible and not self.session_finished:
            text += "_"
        placeholder = "Type something tender or chaotic..."
        color = COLORS.text_light if text else COLORS.accent_ui
        rendered = self.font.render(text or placeholder, color)
        panel.blit(rendered, (16, 16))
        surface.blit(panel, input_rect)

    def _cycle_friend(self, direction: int) -> None:
        self.current_index = (self.current_index + direction) % len(self.friends)

    def _send_message(self, text: str) -> None:
        friend_id, display_name, _ = self.friends[self.current_index]
        convo = self.conversations[friend_id]
        convo.messages.append(ChatMessage("Nadiya", text))
        self.state.apply_outcome(mood=1.0)
        relationship = self.state.relationships.friends.get(friend_id, 50.0)
        threshold = float(self._event_cfg.get("friend_ignore_threshold", 25.0))
        if relationship < threshold:
            convo.messages.append(ChatMessage(display_name, "..."))
            self.summary.append(f"{display_name} ghosted you tonight.")
            self.state.events.trigger("friend_ignores_you")
            penalty = float(self._evening_cfg.get("chat_mood_penalty", -2.0))
            self.state.apply_outcome(mood=penalty)
            return
        if convo.pending_request is not None:
            return
        persona = f"friend_{friend_id}"
        context = {
            "mood": "high" if self.state.stats.mood > 60 else "low" if self.state.stats.mood < 40 else "neutral",
            "day": str(self.state.day),
            "friend": friend_id,
        }
        convo.pending_request = self.ai_client.submit(
            AIRequest("Nadiya", persona, context, text),
            callback=lambda response, fid=friend_id: self._receive_response(fid, response),
            allow_remote=self.state.settings.ai_enabled,
        )

    def _receive_response(self, friend_id: str, text: str) -> None:
        convo = self.conversations.get(friend_id)
        if not convo:
            return
        convo.pending_request = None
        display_name = next(name for fid, name, _ in self.friends if fid == friend_id)
        convo.messages.append(ChatMessage(display_name, text))
        self.summary.append(f"{display_name} lifted your mood with late-night support.")
        self.state.relationships.adjust_friend(friend_id, 2.0)

    def _build_avatar(self, letter: str, color: Tuple[int, int, int]) -> pygame.Surface:
        size = 36
        avatar = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(avatar, color, (size // 2, size // 2), size // 2)
        text_surface = self.small_font.render(letter.upper(), COLORS.text_dark)
        rect = text_surface.get_rect(center=(size // 2, size // 2))
        avatar.blit(text_surface, rect)
        return avatar

    def consume_summary(self) -> List[str]:
        lines = list(dict.fromkeys(self.summary))
        self.summary.clear()
        return lines


class StaticPhoneApp:
    """Minimal stub for non-interactive applications."""

    def __init__(self, title: str, lines: Sequence[str], *, fonts: dict[str, PixelFont]) -> None:
        self.title = title
        self.lines = list(lines)
        self.font = fonts["body"]
        self.small_font = fonts["small"]
        self.request_close = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_RETURN, pygame.K_SPACE):
            self.request_close = True

    def update(self, dt: float) -> None:
        pass

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((24, 22, 32, 230))
        y = 24
        for line in self.lines:
            rendered = self.font.render(line, COLORS.text_light)
            surface.blit(rendered, (20, y))
            y += rendered.get_height() + 10
        hint = self.small_font.render("Esc to go back", COLORS.accent_ui)
        surface.blit(hint, (20, surface.get_height() - 40))

    def consume_summary(self) -> List[str]:
        return []


@dataclass
class PhoneIcon:
    app_id: str
    label: str
    glyph: str
    color: Tuple[int, int, int]


class PhoneOverlay:
    """Handheld phone overlay that can be toggled inside exploration scenes."""

    def __init__(self, state: GameState, ai_client: LocalAIClient, screen: pygame.Surface) -> None:
        self.state = state
        self.ai_client = ai_client
        self.screen = screen
        self.active = False
        self.active_app: Optional[str] = None
        self.selection_index = 0
        self.summary: List[str] = []
        self.completed = False
        self._fonts = {
            "body": PixelFont(base_size=11, scale=2),
            "small": PixelFont(base_size=9, scale=2),
            "title": PixelFont(base_size=13, scale=3, bold=True),
        }
        self.phone_rect = pygame.Rect(0, 0, 360, 620)
        self.phone_rect.center = (screen.get_width() // 2, screen.get_height() // 2)
        self.app_surface = pygame.Surface((self.phone_rect.width - 48, self.phone_rect.height - 140), pygame.SRCALPHA)
        self._apps: Dict[str, object] = {}
        self._icons: List[PhoneIcon] = [
            PhoneIcon("discord", "Discord", "D", COLORS.accent_ui),
            PhoneIcon("gallery", "Gallery", "G", (255, 189, 120)),
            PhoneIcon("notes", "Notes", "N", (128, 210, 182)),
        ]
        self._home_hint_timer = 0.0
        self._build_apps()

    def _build_apps(self) -> None:
        panel_size = (self.app_surface.get_width(), self.app_surface.get_height())
        discord = DiscordApp(
            self.state,
            self.ai_client,
            fonts=self._fonts,
            panel_size=panel_size,
        )
        gallery = StaticPhoneApp(
            "Gallery",
            (
                "Photos: mom's birthday cake", 
                " • fries mid-air action shot",
                " • tram window reflections",
                "More to unlock soon...",
            ),
            fonts=self._fonts,
        )
        notes = StaticPhoneApp(
            "Notes",
            (
                "• Practice umlauts before class",
                "• Remind mom about rent letter",
                "• Stretch wrists before fry shift",
            ),
            fonts=self._fonts,
        )
        self._apps = {
            "discord": discord,
            "gallery": gallery,
            "notes": notes,
        }

    @property
    def discord_app(self) -> DiscordApp:
        return self._apps["discord"]  # type: ignore[return-value]

    def open(self) -> None:
        self.active = True
        self.active_app = None
        self.selection_index = 0
        self._home_hint_timer = 0.0

    def close(self) -> None:
        self.active = False
        self.active_app = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.active:
            return
        if self.active_app:
            app = self._apps[self.active_app]
            app.handle_event(event)
            if getattr(app, "request_close", False):
                self.summary.extend(app.consume_summary())
                setattr(app, "request_close", False)
                self.active_app = None
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.close()
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._open_selected_app()
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self._move_selection(1)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self._move_selection(-1)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.selection_index = 0
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selection_index = min(self.selection_index + 1, len(self._icons) - 1)

    def update(self, dt: float) -> None:
        if not self.active:
            if self.discord_app.session_finished and not self.completed:
                self.summary.extend(self.discord_app.consume_summary())
                if not self.summary:
                    self.summary.append("Phone night scrolled by quietly.")
                self.completed = True
            return
        self._home_hint_timer += dt
        for app_id, app in self._apps.items():
            is_active = self.active_app == app_id and self.active
            if isinstance(app, DiscordApp):
                app.update(dt, active=is_active)
                if app.session_finished and not self.completed:
                    self.summary.extend(app.consume_summary())
                    if not self.summary:
                        self.summary.append("Friend chat soothed the static.")
                    self.completed = True
            else:
                app.update(dt)

    def render(self) -> None:
        if not self.active:
            return
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))
        pygame.draw.rect(self.screen, (24, 22, 30), self.phone_rect, border_radius=28)
        inner_rect = self.phone_rect.inflate(-24, -24)
        pygame.draw.rect(self.screen, (12, 10, 18), inner_rect, border_radius=22)
        screen_rect = inner_rect.inflate(-24, -80)
        header_rect = pygame.Rect(inner_rect.left + 20, inner_rect.top + 16, inner_rect.width - 40, 40)
        self._render_status_bar(header_rect)
        app_rect = self.app_surface.get_rect()
        app_rect.center = screen_rect.center
        if self.active_app:
            app = self._apps[self.active_app]
            self.app_surface.fill((18, 16, 24, 230))
            app.render(self.app_surface)
            self.screen.blit(self.app_surface, app_rect.topleft)
        else:
            self._render_home(self.app_surface)
            self.screen.blit(self.app_surface, app_rect.topleft)

    def _render_status_bar(self, rect: pygame.Rect) -> None:
        bar = pygame.Surface(rect.size, pygame.SRCALPHA)
        bar.fill((28, 24, 36, 220))
        time_surface = self._fonts["small"].render(self.state.formatted_clock(), COLORS.text_light)
        bar.blit(time_surface, (12, rect.height // 2 - time_surface.get_height() // 2))
        signal = self._fonts["small"].render("LTE", COLORS.accent_ui)
        battery = self._fonts["small"].render("89%", COLORS.accent_fries)
        bar.blit(signal, (rect.width - 110, rect.height // 2 - signal.get_height() // 2))
        bar.blit(battery, (rect.width - 56, rect.height // 2 - battery.get_height() // 2))
        self.screen.blit(bar, rect.topleft)

    def _render_home(self, surface: pygame.Surface) -> None:
        surface.fill((16, 14, 22, 220))
        cols = 2
        padding_x = 40
        padding_y = 48
        cell_w = (surface.get_width() - padding_x * 2) // cols
        cell_h = 120
        for idx, icon in enumerate(self._icons):
            row = idx // cols
            col = idx % cols
            x = padding_x + col * cell_w
            y = padding_y + row * cell_h
            rect = pygame.Rect(x, y, cell_w - 20, 100)
            card = pygame.Surface(rect.size, pygame.SRCALPHA)
            selected = idx == self.selection_index
            card_color = (*icon.color, 230) if selected else (38, 34, 52, 210)
            card.fill(card_color)
            glyph = self._fonts["title"].render(icon.glyph, COLORS.text_dark if selected else COLORS.text_light)
            glyph_rect = glyph.get_rect(center=(rect.width // 2, rect.height // 2 - 12))
            card.blit(glyph, glyph_rect)
            label = self._fonts["body"].render(icon.label, COLORS.text_light)
            label_rect = label.get_rect(center=(rect.width // 2, rect.height - 28))
            card.blit(label, label_rect)
            surface.blit(card, rect.topleft)
        hint = self._fonts["small"].render("Arrows to move • Enter to open • Esc to close", COLORS.text_light)
        surface.blit(hint, (surface.get_width() // 2 - hint.get_width() // 2, surface.get_height() - 48))

    def _move_selection(self, delta: int) -> None:
        self.selection_index = (self.selection_index + delta) % len(self._icons)

    def _open_selected_app(self) -> None:
        icon = self._icons[self.selection_index]
        self.active_app = icon.app_id
        app = self._apps.get(icon.app_id)
        if isinstance(app, DiscordApp):
            app.request_close = False

    def consume_summary(self) -> List[str]:
        lines = list(dict.fromkeys(self.summary))
        self.summary.clear()
        return lines


__all__ = ["PhoneOverlay", "DiscordApp", "ChatMessage"]
