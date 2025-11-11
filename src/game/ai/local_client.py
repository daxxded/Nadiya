"""Local AI integration utilities.

The real project is designed to speak to a local LLM server. For this
prototype we provide deterministic fallbacks and a simple hook that can be
extended to call an HTTP endpoint without blocking the main thread.
"""

from __future__ import annotations

import json
import os
import random
import threading
import urllib.error
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
    provider: str = "generic"
    timeout: int = 10
    api_key_env: str = ""
    extra_headers: Dict[str, str] = field(default_factory=dict)
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
                provider=str(data.get("provider", "generic")),
                timeout=int(data.get("timeout", 8)),
                api_key_env=str(data.get("api_key_env", "")),
                extra_headers=data.get("extra_headers", {}),
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
        provider = (self.settings.provider or "generic").lower()
        if provider == "huggingface":
            return self._call_huggingface(request)
        if provider == "openrouter":
            return self._call_openrouter(request)
        if provider == "koboldcpp":
            return self._call_kobold(request)
        return self._call_generic(request)

    def _build_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        headers.update({k: str(v) for k, v in self.settings.extra_headers.items()})
        if self.settings.api_key_env:
            key = os.getenv(self.settings.api_key_env, "")
            if key:
                headers.setdefault("Authorization", f"Bearer {key}")
        return headers

    def _call_generic(self, request: AIRequest) -> Optional[str]:
        if not self.settings.endpoint:
            return None
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
                headers=self._build_headers(),
            )
            with urllib.request.urlopen(req, timeout=self.settings.timeout) as resp:
                body = resp.read().decode("utf-8")
            data = json.loads(body)
            return str(data.get("response") or data.get("text") or data.get("data") or "")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
            return None

    def _call_kobold(self, request: AIRequest) -> Optional[str]:
        endpoint = self.settings.endpoint or "http://localhost:5001/api/v1/generate"
        payload = {
            "prompt": request.prompt,
            "max_length": request.max_tokens,
            "temperature": request.temperature,
        }
        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=self._build_headers(),
            )
            with urllib.request.urlopen(req, timeout=self.settings.timeout) as resp:
                body = resp.read().decode("utf-8")
            data = json.loads(body)
            if isinstance(data, dict):
                if "results" in data and data["results"]:
                    return str(data["results"][0].get("text", ""))
                return str(data.get("text", ""))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
            return None
        return None

    def _call_huggingface(self, request: AIRequest) -> Optional[str]:
        model = self.settings.model or "google/gemma-2b-it"
        endpoint = self.settings.endpoint or f"https://api-inference.huggingface.co/models/{model}"
        headers = self._build_headers()
        payload = {
            "inputs": request.prompt,
            "parameters": {
                "temperature": max(0.01, request.temperature),
                "max_new_tokens": request.max_tokens,
                "return_full_text": False,
            },
        }
        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
            )
            with urllib.request.urlopen(req, timeout=self.settings.timeout) as resp:
                body = resp.read().decode("utf-8")
            data = json.loads(body)
            if isinstance(data, list) and data:
                generated = data[0].get("generated_text")
                if generated:
                    return str(generated)
            if isinstance(data, dict):
                for key in ("generated_text", "text", "answer"):
                    if key in data:
                        return str(data[key])
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
            return None
        return None

    def _call_openrouter(self, request: AIRequest) -> Optional[str]:
        endpoint = self.settings.endpoint or "https://openrouter.ai/api/v1/chat/completions"
        headers = self._build_headers()
        headers.setdefault("HTTP-Referer", "https://github.com")
        headers.setdefault("X-Title", "Nadiya Simulator")
        payload = {
            "model": self.settings.model or "meta-llama/llama-3.1-8b-instruct",
            "messages": [
                {"role": "system", "content": self.settings.fallback_personas.get(request.persona, request.persona)},
                {"role": "user", "content": request.prompt},
            ],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
            )
            with urllib.request.urlopen(req, timeout=self.settings.timeout) as resp:
                body = resp.read().decode("utf-8")
            data = json.loads(body)
            if isinstance(data, dict):
                choices = data.get("choices")
                if choices:
                    message = choices[0].get("message", {})
                    return str(message.get("content", ""))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
            return None
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
        if persona == "friend_mina":
            return self._friend_stub("Mina", prompt, context_flags)
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
