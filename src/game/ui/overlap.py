"""Utility to detect overlapping UI widgets during rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import pygame


@dataclass
class TrackedRect:
    rect: pygame.Rect
    tag: str
    allow_overlap: bool


class UIOverlapMonitor:
    """Keeps track of rendered rectangles and reports unintended overlaps."""

    def __init__(self) -> None:
        self._entries: List[TrackedRect] = []
        self.collisions: Dict[Tuple[str, str], pygame.Rect] = {}

    def reset(self) -> None:
        self._entries.clear()
        self.collisions.clear()

    def register(self, rect: pygame.Rect, tag: str, *, allow_overlap: bool = False) -> None:
        tracked = TrackedRect(rect.copy(), tag, allow_overlap)
        for other in self._entries:
            if tracked.rect.colliderect(other.rect):
                if tracked.allow_overlap or other.allow_overlap:
                    continue
                key = tuple(sorted((tracked.tag, other.tag)))
                if key not in self.collisions:
                    intersection = tracked.rect.clip(other.rect)
                    self.collisions[key] = intersection
        self._entries.append(tracked)

    def overlaps(self) -> Dict[Tuple[str, str], pygame.Rect]:
        """Return mapping of problematic overlaps detected this frame."""

        return dict(self.collisions)


__all__ = ["UIOverlapMonitor"]
