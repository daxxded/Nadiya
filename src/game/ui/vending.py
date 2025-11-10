"""Overlay representing a vending machine interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

import pygame

from game.balance import get_balance_section
from game.config import COLORS
from game.state import GameState
from game.ui.fonts import PixelFont


@dataclass
class VendingItem:
    id: str
    label: str
    price: float
    hunger: float


class VendingMachineUI:
    def __init__(self, state: GameState, screen: pygame.Surface) -> None:
        self.state = state
        self.screen = screen
        self.font = PixelFont(base_size=11, scale=2)
        self.small_font = PixelFont(base_size=9, scale=2)
        self.title_font = PixelFont(base_size=13, scale=3, bold=True)
        self.items: Sequence[VendingItem] = self._load_items()
        self.selection = 0
        self.active = False
        self.feedback_timer = 0.0
        self.feedback_text = ""
        self.summary: List[str] = []

    def _load_items(self) -> Sequence[VendingItem]:
        config = get_balance_section("vending").get("items", [])
        items: List[VendingItem] = []
        for entry in config:
            item = VendingItem(
                id=str(entry.get("id", "item")),
                label=str(entry.get("label", "Snack")),
                price=float(entry.get("price", 2.0)),
                hunger=float(entry.get("hunger", 5.0)),
            )
            items.append(item)
        return items or [VendingItem("bar", "Mystery Bar", 2.5, 6.0)]

    def open(self) -> None:
        self.active = True
        self.selection = 0
        self.feedback_timer = 0.0
        self.feedback_text = ""

    def close(self) -> None:
        self.active = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.active:
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.close()
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selection = (self.selection + 1) % len(self.items)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.selection = (self.selection - 1) % len(self.items)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._purchase()

    def update(self, dt: float) -> None:
        if self.feedback_timer > 0:
            self.feedback_timer -= dt
            if self.feedback_timer <= 0:
                self.feedback_text = ""

    def render(self) -> None:
        if not self.active:
            return
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        panel = pygame.Surface((460, 420), pygame.SRCALPHA)
        panel.fill((24, 24, 32, 240))
        rect = panel.get_rect()
        rect.center = (self.screen.get_width() // 2, self.screen.get_height() // 2)
        title = self.title_font.render("Vending Machine", COLORS.accent_ui)
        panel.blit(title, (20, 20))
        for idx, item in enumerate(self.items):
            y = 80 + idx * 70
            highlight = idx == self.selection
            bg = pygame.Surface((rect.width - 60, 60), pygame.SRCALPHA)
            bg.fill((46, 40, 64, 220) if highlight else (36, 32, 48, 200))
            panel.blit(bg, (30, y))
            label = self.font.render(item.label, COLORS.text_light)
            price = self.font.render(f"€{item.price:.2f}", COLORS.accent_fries if highlight else COLORS.text_light)
            hunger = self.small_font.render(f"Hunger +{item.hunger:.0f}", COLORS.accent_cool)
            panel.blit(label, (48, y + 12))
            panel.blit(price, (rect.width - price.get_width() - 56, y + 12))
            panel.blit(hunger, (48, y + 36))
        if self.feedback_text:
            feedback = self.small_font.render(self.feedback_text, COLORS.accent_fries)
            panel.blit(feedback, (40, rect.height - 70))
        hint = self.small_font.render("Enter to buy • Esc to close", COLORS.text_light)
        panel.blit(hint, (40, rect.height - 40))
        self.screen.blit(panel, rect)

    def consume_summary(self) -> List[str]:
        lines = list(self.summary)
        self.summary.clear()
        return lines

    def _purchase(self) -> None:
        if not self.items:
            self.feedback_text = "Empty machine."
            self.feedback_timer = 1.2
            return
        item = self.items[self.selection]
        if self.state.stats.money < item.price:
            self.feedback_text = "Not enough coins."
            self.feedback_timer = 1.4
            return
        self.state.stats.adjust_money(-item.price)
        self.state.apply_outcome(hunger=item.hunger, mood=1.0)
        self.feedback_text = f"Bought {item.label}!"
        self.feedback_timer = 1.6
        self.summary.append(f"Grabbed {item.label} from the vending machine.")


__all__ = ["VendingMachineUI", "VendingItem"]
