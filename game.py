"""Convenience entrypoint for launching the Nadiya Simulator prototype."""
from __future__ import annotations

import sys
from pathlib import Path


def _ensure_src_on_path() -> None:
    """Add the repository's ``src`` directory to ``sys.path`` if needed."""
    root = Path(__file__).resolve().parent
    src = root / "src"
    src_str = str(src)
    if src.exists() and src_str not in sys.path:
        sys.path.insert(0, src_str)


def main() -> int:
    """Entrypoint proxy that delegates to ``game.main``."""
    _ensure_src_on_path()
    from game.main import main as game_main  # import here after adjusting path

    return game_main()


if __name__ == "__main__":
    raise SystemExit(main())
