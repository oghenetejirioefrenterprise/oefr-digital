"""Vertical-specialized harvest plugin registry.

Each plugin module exposes a `harvest(brief: dict, workspace: Path) -> Path | None`
function returning the cleaned CSV path on success, or None to fall back to generic harvest.

Niche keyword → plugin module mapping. data-engineer agent consults this registry
before falling back to generic Google-operator-based harvest.
"""
from __future__ import annotations
from importlib import import_module
from pathlib import Path
from typing import Callable, Optional

# Keyword → module name (in this package)
REGISTRY: dict[str, str] = {
    "real estate permit": "real_estate_permits",
    "building permit": "real_estate_permits",
    "construction permit": "real_estate_permits",
    "demolition permit": "real_estate_permits",
}


def find_plugin(niche_text: str) -> Optional[str]:
    """Return module name of best-matching plugin for `niche_text`, or None."""
    lowered = niche_text.lower()
    for keyword, module_name in REGISTRY.items():
        if keyword in lowered:
            return module_name
    return None


def get_harvester(module_name: str) -> Callable:
    """Import and return the harvester function from `module_name`."""
    mod = import_module(f"scripts.harvesters.{module_name}")
    return mod.harvest
