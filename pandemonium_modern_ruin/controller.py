from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pandemonium_modern_ruin.persistence import load_game, save_game
from pandemonium_modern_ruin.simulation import Simulation, TurnOutcome


@dataclass
class GameController:
    simulation: Simulation

    @classmethod
    def new(cls, *, seed: int | None = None, city_name: str = "New Carthage") -> GameController:
        return cls(Simulation.new(seed=seed, city_name=city_name))

    @classmethod
    def load(cls, path: str | Path) -> GameController:
        return cls(load_game(path))

    def cast(self, ability_key: str, target: str | None = None) -> TurnOutcome:
        return self.simulation.perform_ability(ability_key, target)

    def wait(self) -> TurnOutcome:
        return self.simulation.wait()

    def save(self, path: str | Path) -> Path:
        return save_game(self.simulation, path)

    def load_into_self(self, path: str | Path) -> None:
        self.simulation = load_game(path)
