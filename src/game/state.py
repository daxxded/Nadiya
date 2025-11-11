"""Game state management for Nadiya Simulator."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List

from game.balance import get_balance_section
from game.events import EventSystem
from game.settings import UserSettings


class TimeSegment(Enum):
    DAWN = auto()
    COMMUTE = auto()
    MORNING = auto()
    AFTERNOON = auto()
    EVENING = auto()
    NIGHT = auto()


@dataclass
class Relationships:
    mom: float = 50.0
    friends: Dict[str, float] = field(
        default_factory=lambda: {"zara": 50.0, "lukas": 50.0, "mina": 50.0}
    )

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
    money: float = 10.0

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

    def adjust_money(self, delta: float) -> None:
        self.money = float(max(0.0, self.money + delta))


@dataclass
class EventFlags:
    seen_dreams: List[str] = field(default_factory=list)
    mom_modes: Dict[int, str] = field(default_factory=dict)


@dataclass
class GameState:
    day: int = 1
    segment: TimeSegment = TimeSegment.DAWN
    stats: PlayerStats = field(default_factory=PlayerStats)
    relationships: Relationships = field(default_factory=Relationships)
    flags: EventFlags = field(default_factory=EventFlags)
    events: EventSystem = field(default_factory=EventSystem)
    settings: UserSettings = field(default_factory=UserSettings)
    segment_time: float = 0.0
    segment_duration: float = 30.0
    segment_start_minutes: float = 420.0
    segment_duration_minutes: float = 120.0
    day_minutes: float = 420.0
    skip_requested: bool = False

    def __post_init__(self) -> None:
        self._recalculate_segment(self.segment)

    def advance_segment(self) -> None:
        order = [
            TimeSegment.DAWN,
            TimeSegment.COMMUTE,
            TimeSegment.MORNING,
            TimeSegment.AFTERNOON,
            TimeSegment.EVENING,
            TimeSegment.NIGHT,
        ]
        idx = order.index(self.segment)
        if idx == len(order) - 1:
            self.segment = TimeSegment.MORNING
            self.day += 1
            self.handle_new_day()
        else:
            self.segment = order[idx + 1]
        self._recalculate_segment(self.segment)

    def handle_new_day(self) -> None:
        sleep_cfg = get_balance_section("sleep")
        self.stats.apply_energy(float(sleep_cfg.get("base_restore", 30)))
        self.stats.apply_mood(float(sleep_cfg.get("mood_bonus", 5)))
        self.stats.apply_hunger(float(sleep_cfg.get("hunger_decay", -8)))
        self.events.new_day()
        self._recalculate_segment(self.segment)

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

    def start_segment(self, segment: TimeSegment) -> None:
        self.segment = segment
        self._recalculate_segment(segment)

    def tick_clock(self, dt: float) -> None:
        if self.segment_duration <= 0:
            self.segment_time = 0.0
            return
        self.segment_time = min(self.segment_time + dt, self.segment_duration)
        progress = min(1.0, self.segment_time / self.segment_duration)
        self.day_minutes = self.segment_start_minutes + progress * self.segment_duration_minutes

    def request_skip(self) -> None:
        self.skip_requested = True

    def consume_skip_request(self) -> bool:
        if self.skip_requested:
            self.skip_requested = False
            return True
        return False

    def _recalculate_segment(self, segment: TimeSegment) -> None:
        segments_cfg = get_balance_section("segments")
        key = segment.name.lower()
        cfg = segments_cfg.get(key, {})
        self.segment_duration = float(cfg.get("base_timer", 30.0))
        start_minutes = float(cfg.get("clock_start", self.segment_start_minutes))
        end_minutes = float(cfg.get("clock_end", start_minutes + max(30.0, self.segment_duration * 4)))
        self.segment_start_minutes = start_minutes
        self.segment_duration_minutes = max(1.0, end_minutes - start_minutes)
        self.segment_time = 0.0
        self.day_minutes = start_minutes

    def formatted_clock(self) -> str:
        hours = int(self.day_minutes // 60) % 24
        minutes = int(self.day_minutes % 60)
        return f"{hours:02d}:{minutes:02d}"


__all__ = ["GameState", "TimeSegment", "PlayerStats", "Relationships", "EventFlags"]
