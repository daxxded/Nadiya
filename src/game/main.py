"""Entrypoint for the Nadiya Simulator playable prototype."""

from __future__ import annotations

import argparse
import sys

import pygame
import pygame.freetype

from game.ai.local_client import LocalAIClient
from game.config import BASE_HEIGHT, BASE_WIDTH
from game.scene_controller import SceneController
from game.state import GameState


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Nadiya Simulator prototype")
    parser.add_argument("--headless", action="store_true", help="Initialize pygame without opening a window (for CI)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pygame.init()
    pygame.freetype.init()
    flags = pygame.HIDDEN if args.headless else 0
    screen = pygame.display.set_mode((BASE_WIDTH, BASE_HEIGHT), flags=flags)
    pygame.display.set_caption("Nadiya Simulator")

    state = GameState()
    ai_client = LocalAIClient()
    controller = SceneController(state, screen, ai_client)

    running = True
    max_headless_frames = 300 if args.headless else None
    frames = 0
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            else:
                controller.handle_event(event)
        controller.update()
        if max_headless_frames is not None:
            frames += 1
            if frames >= max_headless_frames:
                running = False

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
