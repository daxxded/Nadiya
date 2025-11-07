"""Game state management for Nadiya Simulator."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List

from game.balance import get_balance_section
from game.events import EventSystem


class TimeSegment(Enum):
    MORNING = auto()
    AFTERNOON = auto()
    EVENING = auto()
    NIGHT = auto()


@dataclass
class Relationships:
    mom: float = 50.0
    friends: Dict[str, float] = field(default_factory=lambda: {"zara": 50.0, "lukas": 50.0})

    def adjust_friend(self, friend_id: str, delta: float) -> None:
        self.friends.setdefault(friend_id, 50.0)
        self.friends[friend_id] = float(min(100.0, max(0.0, self.friends[friend_id] + delta)))

    def adjust_mom(self, delta: float) -> None:
        self.mom = float(min(100.0, max(0.0, self.mom + delta)))


@dataclass
class PlayerStats:
    mood: float = 60.0
    hunger: float = 40.0
    energy: float = 70.0
    german_xp: float = 0.0
    german_level: int = 1

    def clamp(self) -> None:
        self.mood = float(min(100.0, max(0.0, self.mood)))
        self.hunger = float(min(100.0, max(0.0, self.hunger)))
        self.energy = float(min(100.0, max(0.0, self.energy)))

    def apply_mood(self, delta: float) -> None:
        self.mood += delta
        self.clamp()

    def apply_hunger(self, delta: float) -> None:
        self.hunger += delta
        self.clamp()

    def apply_energy(self, delta: float) -> None:
        self.energy += delta
        self.clamp()

    def add_german_xp(self, amount: float) -> None:
        self.german_xp += amount
        # Level thresholds: 0-99 -> 1, 100-249 -> 2, 250+ -> 3, etc.
        new_level = int(self.german_xp // 150) + 1
        if new_level != self.german_level:
            self.german_level = new_level


@dataclass
class EventFlags:
    seen_dreams: List[str] = field(default_factory=list)
    mom_modes: Dict[int, str] = field(default_factory=dict)


@dataclass
class GameState:
    day: int = 1
    segment: TimeSegment = TimeSegment.MORNING
    stats: PlayerStats = field(default_factory=PlayerStats)
    relationships: Relationships = field(default_factory=Relationships)
    flags: EventFlags = field(default_factory=EventFlags)
    events: EventSystem = field(default_factory=EventSystem)

    def advance_segment(self) -> None:
        order = [TimeSegment.MORNING, TimeSegment.AFTERNOON, TimeSegment.EVENING, TimeSegment.NIGHT]
        idx = order.index(self.segment)
        if idx == len(order) - 1:
            self.segment = TimeSegment.MORNING
            self.day += 1
            self.handle_new_day()
        else:
            self.segment = order[idx + 1]

    def handle_new_day(self) -> None:
        sleep_cfg = get_balance_section("sleep")
        self.stats.apply_energy(float(sleep_cfg.get("base_restore", 30)))
        self.stats.apply_mood(float(sleep_cfg.get("mood_bonus", 5)))
        self.stats.apply_hunger(float(sleep_cfg.get("hunger_decay", -8)))
        self.events.new_day()

    def apply_outcome(self, mood: float = 0.0, hunger: float = 0.0, energy: float = 0.0, german_xp: float = 0.0) -> None:
        if mood:
            self.stats.apply_mood(mood)
        if hunger:
            self.stats.apply_hunger(hunger)
        if energy:
            self.stats.apply_energy(energy)
        if german_xp:
            self.stats.add_german_xp(german_xp)

    def fatigue_modifier(self) -> float:
        if self.stats.energy < 30:
            return 0.6
        if self.stats.energy < 50:
            return 0.8
        return 1.0

    def focus_modifier(self) -> float:
        if self.stats.mood > 70:
            return 1.15
        if self.stats.mood < 30:
            return 0.8
        return 1.0

    def mood_descriptor(self) -> str:
        if self.stats.mood >= 70:
            return "bright-eyed"
        if self.stats.mood <= 30:
            return "frayed"
        return "somewhere between tired and hopeful"

    def should_force_rest(self) -> bool:
        night_cfg = get_balance_section("segments").get("night", {})
        mood_floor = float(night_cfg.get("mood_floor", 15))
        return self.stats.energy <= 5 or self.stats.mood <= mood_floor


__all__ = ["GameState", "TimeSegment", "PlayerStats", "Relationships", "EventFlags"]
