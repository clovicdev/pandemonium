from __future__ import annotations

import json
from pathlib import Path

from pandemonium_modern_ruin.exceptions import SaveGameError
from pandemonium_modern_ruin.simulation import Simulation


def save_game(simulation: Simulation, path: str | Path) -> Path:
    destination = Path(path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        destination.write_text(json.dumps(simulation.as_dict(), indent=2), encoding="utf-8")
    except OSError as exc:
        raise SaveGameError(f"Couldn't save the game to: {destination}") from exc
    return destination


def load_game(path: str | Path) -> Simulation:
    source = Path(path).expanduser().resolve()
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SaveGameError(f"Couldn't open the saved game: {source}") from exc
    if not isinstance(payload, dict):
        raise SaveGameError(f"That file isn't a saved game: {source}")
    try:
        return Simulation.from_mapping(payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise SaveGameError(f"That save is broken or too old: {source}") from exc
