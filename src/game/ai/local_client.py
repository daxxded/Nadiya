"""Local AI integration utilities.

The real project is designed to speak to a local LLM server. For this
prototype we provide deterministic fallbacks and a simple hook that can be
extended to call an HTTP endpoint without blocking the main thread.
"""

from __future__ import annotations

import json
import random
import threading
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional

import pygame

from game.config import PROJECT_ROOT


@dataclass
class AIRequest:
    """Container describing an AI generation request."""

    speaker: str
    persona: str
    context: Dict[str, str]
    prompt: str
    temperature: float = 0.2
    max_tokens: int = 120


@dataclass
class LocalAISettings:
    enabled: bool = False
    endpoint: str = ""
    model: str = ""
    timeout: int = 10
    fallback_personas: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls) -> "LocalAISettings":
        settings_path = PROJECT_ROOT / "data" / "ai" / "settings.json"
        if settings_path.exists():
            with settings_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            return cls(
                enabled=bool(data.get("enabled", False)),
                endpoint=str(data.get("endpoint", "")),
                model=str(data.get("model", "")),
                timeout=int(data.get("timeout", 8)),
                fallback_personas=data.get("fallback_personas", {}),
            )
        return cls(fallback_personas={})


class LocalAIClient:
    """Very small asynchronous dispatcher for AI replies."""

    def __init__(self) -> None:
        self.pending: List[AIRequest] = []
        self.responses: Dict[int, str] = {}
        self._counter = 0
        self._lock = threading.Lock()
        self.settings = LocalAISettings.load()

    def submit(self, request: AIRequest, callback: Optional[Callable[[str], None]] = None, *, allow_remote: bool = True) -> int:
        with self._lock:
            request_id = self._counter
            self._counter += 1
        self.pending.append(request)
        threading.Thread(target=self._run_generation, args=(request_id, request, callback, allow_remote), daemon=True).start()
        return request_id

    def _run_generation(self, request_id: int, request: AIRequest, callback: Optional[Callable[[str], None]], allow_remote: bool) -> None:
        if allow_remote and self.settings.enabled:
            response = self._call_http(request)
        else:
            response = None
        if not response:
            response = self._generate_stub(request)
        response = self._sanitize(response)
        with self._lock:
            self.responses[request_id] = response
        if callback:
            callback(response)

    def _call_http(self, request: AIRequest) -> Optional[str]:
        payload = {
            "model": self.settings.model,
            "prompt": request.prompt,
            "system": self.settings.fallback_personas.get(request.persona, request.persona),
            "context": request.context,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        try:
            req = urllib.request.Request(
                self.settings.endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.settings.timeout) as resp:
                body = resp.read().decode("utf-8")
            data = json.loads(body)
            return str(data.get("response") or data.get("text") or "")
        except Exception:
            return None

    def poll_response(self, request_id: int) -> Optional[str]:
        return self.responses.get(request_id)

    def _generate_stub(self, request: AIRequest) -> str:
        persona = request.persona
        prompt = request.prompt.lower()
        context_flags = ", ".join(f"{k}:{v}" for k, v in sorted(request.context.items()))
        if persona == "mom":
            return self._mom_stub(prompt, context_flags)
        if persona == "friend_zara":
            return self._friend_stub("Zara", prompt, context_flags)
        if persona == "friend_lukas":
            return self._friend_stub("Lukas", prompt, context_flags)
        return "I'm not sure what to say right now, but I'm here."

    def _mom_stub(self, prompt: str, context_flags: str) -> str:
        mood_tag = "" if "mood:high" not in context_flags else " She notices your spark."
        if "tired" in context_flags:
            return "Mom sighs, rubs her temples, and admits she's just exhausted from the day." + mood_tag
        if "drunk" in context_flags:
            return "Mom leans in with a conspiratorial grin, oversharing a bittersweet memory about her twenties." + mood_tag
        return "Mom offers a small smile and asks how the fries went tonight." + mood_tag

    def _friend_stub(self, name: str, prompt: str, context_flags: str) -> str:
        if "homework" in prompt:
            return f"{name}: haha, your homework is basically improv theatre, you'll nail it."
        if "tired" in prompt:
            return f"{name}: same, my brain is mashed potatoes, but at least we tried."
        if "fries" in prompt:
            return f"{name}: your fries are legendary, even if they try to maim you."
        # Weighted randomness for variety
        choices = [
            f"{name}: tell me one weird thing from school today.",
            f"{name}: do you need a playlist? I curated a mood-saver mix.",
            f"{name}: breathe, drink water, keep being chaos incarnate."
        ]
        return random.choice(choices)

    def _sanitize(self, text: str) -> str:
        cleaned = text.replace("\r", " ").strip()
        if len(cleaned) > 240:
            cleaned = cleaned[:237] + "..."
        return cleaned


class DialogueBubble(pygame.sprite.Sprite):
    """Simple sprite to display AI generated text in the world."""

    def __init__(self, text: str, position: pygame.math.Vector2, font: pygame.font.Font) -> None:
        super().__init__()
        padding = 8
        rendered = font.render(text, True, (32, 24, 20))
        self.image = pygame.Surface((rendered.get_width() + padding * 2, rendered.get_height() + padding * 2), pygame.SRCALPHA)
        pygame.draw.rect(self.image, (255, 240, 220, 240), self.image.get_rect(), border_radius=6)
        self.image.blit(rendered, (padding, padding))
        self.rect = self.image.get_rect()
        self.rect.center = (int(position.x), int(position.y))


def serialize_ai_request(request: AIRequest) -> str:
    return json.dumps(request.__dict__)


__all__ = ["AIRequest", "LocalAIClient", "DialogueBubble", "serialize_ai_request"]
