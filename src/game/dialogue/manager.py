"""Simple branching dialogue system backed by JSON definitions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List

from game.config import PROJECT_ROOT
from game.events import EventSystem

_DIALOGUE_PATH = PROJECT_ROOT / "data" / "dialogue" / "bank.json"


@dataclass
class DialogueChoice:
    id: str
    text: str
    next: str | None = None


@dataclass
class DialogueNode:
    node_id: str
    lines: List[str]
    choices: List[DialogueChoice]


class DialogueManager:
    def __init__(self) -> None:
        if not _DIALOGUE_PATH.exists():
            raise FileNotFoundError(f"Dialogue bank missing at {_DIALOGUE_PATH}")
        with _DIALOGUE_PATH.open("r", encoding="utf-8") as fh:
            self._raw: Dict[str, Dict[str, Dict[str, object]]] = json.load(fh)

    def _resolve_node(self, character: str, node_key: str, events: EventSystem) -> DialogueNode | None:
        definitions = self._raw.get(character, {})
        data = definitions.get(node_key)
        if not data:
            return None
        required: List[str] = data.get("requires", [])  # type: ignore[assignment]
        if any(not events.was_triggered_today(flag) for flag in required):
            return None
        lines = [str(line) for line in data.get("lines", [])]
        choices_data = data.get("choices", [])
        choices = [DialogueChoice(str(item.get("id")), str(item.get("text")), item.get("next")) for item in choices_data]
        return DialogueNode(node_key, lines, choices)

    def start(self, character: str, preferred_nodes: List[str], events: EventSystem) -> DialogueNode | None:
        for node_key in preferred_nodes:
            node = self._resolve_node(character, node_key, events)
            if node:
                return node
        return None


__all__ = ["DialogueManager", "DialogueNode"]
