"""Global configuration constants for Nadiya Simulator prototype."""

import pathlib
from dataclasses import dataclass

# Screen dimensions and scaling factors
BASE_WIDTH = 1280
BASE_HEIGHT = 720
FPS = 60

# Isometric tile sizing (diamond tiles)
TILE_WIDTH = 128
TILE_HEIGHT = 64

# Paths
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
ASSETS_DIR = PROJECT_ROOT / "assets"


@dataclass(frozen=True)
class ColorPalette:
    """Color palette aligned with the warm neutral art direction."""

    warm_neutral = (216, 200, 184)
    warm_dark = (92, 72, 60)
    accent_fries = (255, 199, 44)
    accent_ui = (240, 96, 96)
    accent_cool = (112, 170, 199)
    text_dark = (48, 40, 32)
    text_light = (248, 244, 240)


COLORS = ColorPalette()
