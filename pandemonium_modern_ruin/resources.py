from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from pandemonium_modern_ruin.exceptions import InsufficientResources


class ResourceType(str, Enum):
    TERROR = "terror"
    CORRUPTION = "corruption"
    CHAOS = "chaos"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ResourceDelta:
    terror: float = 0.0
    corruption: float = 0.0
    chaos: float = 0.0

    def __add__(self, other: ResourceDelta) -> ResourceDelta:
        return ResourceDelta(
            terror=self.terror + other.terror,
            corruption=self.corruption + other.corruption,
            chaos=self.chaos + other.chaos,
        )

    def __neg__(self) -> ResourceDelta:
        return ResourceDelta(-self.terror, -self.corruption, -self.chaos)

    def values(self) -> dict[str, float]:
        return {
            ResourceType.TERROR.value: self.terror,
            ResourceType.CORRUPTION.value: self.corruption,
            ResourceType.CHAOS.value: self.chaos,
        }

    def rounded(self) -> ResourceDelta:
        return ResourceDelta(round(self.terror, 2), round(self.corruption, 2), round(self.chaos, 2))

    @classmethod
    def from_mapping(cls, payload: Mapping[str, float]) -> ResourceDelta:
        return cls(
            terror=float(payload.get(ResourceType.TERROR.value, 0.0)),
            corruption=float(payload.get(ResourceType.CORRUPTION.value, 0.0)),
            chaos=float(payload.get(ResourceType.CHAOS.value, 0.0)),
        )


@dataclass
class ResourceLedger:
    terror: float = 28.0
    corruption: float = 20.0
    chaos: float = 14.0

    def can_pay(self, cost: ResourceDelta) -> bool:
        return (
            self.terror + 1e-9 >= max(cost.terror, 0.0)
            and self.corruption + 1e-9 >= max(cost.corruption, 0.0)
            and self.chaos + 1e-9 >= max(cost.chaos, 0.0)
        )

    def pay(self, cost: ResourceDelta, *, reason: str) -> None:
        if not self.can_pay(cost):
            current = self.as_compact_text()
            needed = _format_delta(cost)
            raise InsufficientResources(f"Need {needed}. You have {current}.")
        self.credit(-cost)

    def credit(self, delta: ResourceDelta) -> None:
        self.terror = max(0.0, self.terror + delta.terror)
        self.corruption = max(0.0, self.corruption + delta.corruption)
        self.chaos = max(0.0, self.chaos + delta.chaos)

    def as_dict(self) -> dict[str, float]:
        return {
            ResourceType.TERROR.value: self.terror,
            ResourceType.CORRUPTION.value: self.corruption,
            ResourceType.CHAOS.value: self.chaos,
        }

    def as_compact_text(self) -> str:
        return (
            f"Terror {self.terror:.1f}, "
            f"Corruption {self.corruption:.1f}, "
            f"Chaos {self.chaos:.1f}"
        )

    @classmethod
    def from_mapping(cls, payload: Mapping[str, float]) -> ResourceLedger:
        return cls(
            terror=float(payload.get(ResourceType.TERROR.value, 0.0)),
            corruption=float(payload.get(ResourceType.CORRUPTION.value, 0.0)),
            chaos=float(payload.get(ResourceType.CHAOS.value, 0.0)),
        )


def _format_delta(delta: ResourceDelta) -> str:
    parts: list[str] = []
    for name, value in delta.values().items():
        if value > 0:
            parts.append(f"{value:.1f} {name.title()}")
    return ", ".join(parts) if parts else "no resources"
