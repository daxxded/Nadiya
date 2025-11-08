"""Player-facing configurable settings."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UserSettings:
    music_volume: float = 0.6
    sfx_volume: float = 0.8
    text_speed: float = 1.0
    ai_enabled: bool = False

    def clamp(self) -> None:
        self.music_volume = float(min(1.0, max(0.0, self.music_volume)))
        self.sfx_volume = float(min(1.0, max(0.0, self.sfx_volume)))
        self.text_speed = float(min(2.5, max(0.5, self.text_speed)))


__all__ = ["UserSettings"]
