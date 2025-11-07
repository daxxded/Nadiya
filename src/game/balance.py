"""Runtime loading for balancing hooks defined in JSON."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Dict

from game.config import PROJECT_ROOT

_BALANCE_PATH = PROJECT_ROOT / "data" / "balance.json"


class BalanceError(RuntimeError):
    """Raised when balance configuration cannot be loaded."""


@lru_cache(maxsize=1)
def load_balance() -> Dict[str, Any]:
    if not _BALANCE_PATH.exists():
        raise BalanceError(f"Missing balance configuration at {_BALANCE_PATH}")
    with _BALANCE_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def get_balance_section(section: str) -> Dict[str, Any]:
    data = load_balance()
    try:
        return data[section]
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise BalanceError(f"Section '{section}' not found in balance configuration") from exc


__all__ = ["load_balance", "get_balance_section", "BalanceError"]
