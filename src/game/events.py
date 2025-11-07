"""Centralized event and flag tracking for narrative branching."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Set


@dataclass
class DailyEventLog:
    """Tracks events triggered during a single in-game day."""

    triggered: Set[str] = field(default_factory=set)

    def register(self, event_id: str) -> None:
        self.triggered.add(event_id)

    def reset(self) -> None:
        self.triggered.clear()

    def has(self, event_id: str) -> bool:
        return event_id in self.triggered


@dataclass
class PersistentFlags:
    """Flags that carry over between days."""

    values: Dict[str, int] = field(default_factory=dict)

    def bump(self, flag_id: str, amount: int = 1) -> None:
        self.values[flag_id] = self.values.get(flag_id, 0) + amount

    def set(self, flag_id: str, value: int) -> None:
        self.values[flag_id] = value

    def get(self, flag_id: str, default: int = 0) -> int:
        return self.values.get(flag_id, default)

    def clear_many(self, flags: Iterable[str]) -> None:
        for flag in flags:
            self.values.pop(flag, None)


@dataclass
class EventSystem:
    """Container glued onto :class:`~game.state.GameState`."""

    daily: DailyEventLog = field(default_factory=DailyEventLog)
    persistent: PersistentFlags = field(default_factory=PersistentFlags)

    def new_day(self) -> None:
        self.daily.reset()

    def trigger(self, event_id: str) -> None:
        self.daily.register(event_id)
        self.persistent.bump(f"count:{event_id}")

    def was_triggered_today(self, event_id: str) -> bool:
        return self.daily.has(event_id)

    def total_occurrences(self, event_id: str) -> int:
        return self.persistent.get(f"count:{event_id}")


__all__ = ["EventSystem"]
