from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol

from pandemonium_modern_ruin.resources import ResourceDelta


class CityView(Protocol):
    morale: float

    def average_integrity(self) -> float: ...

    def average_trust(self) -> float: ...


@dataclass(frozen=True)
class CityCondition(ABC):
    key: str
    label: str
    description: str

    @property
    @abstractmethod
    def response_multiplier(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def resource_pulse(self, city: CityView) -> ResourceDelta:
        raise NotImplementedError


class StableCity(CityCondition):
    def __init__(self) -> None:
        super().__init__(
            key="stable",
            label="Stable",
            description="The city still believes tomorrow will resemble today.",
        )

    @property
    def response_multiplier(self) -> float:
        return 1.0

    def resource_pulse(self, city: CityView) -> ResourceDelta:
        return ResourceDelta(terror=1.2, corruption=0.7, chaos=0.4)


class StrainedCity(CityCondition):
    def __init__(self) -> None:
        super().__init__(
            key="strained",
            label="Strained",
            description="Failures rhyme often enough that citizens start seeing patterns.",
        )

    @property
    def response_multiplier(self) -> float:
        return 0.92

    def resource_pulse(self, city: CityView) -> ResourceDelta:
        trust_loss = max(0.0, 100.0 - city.average_trust())
        return ResourceDelta(terror=2.4, corruption=1.2 + trust_loss / 90.0, chaos=0.9)


class CrisisCity(CityCondition):
    def __init__(self) -> None:
        super().__init__(
            key="crisis",
            label="Crisis",
            description="The official story cannot keep pace with lived reality.",
        )

    @property
    def response_multiplier(self) -> float:
        return 0.78

    def resource_pulse(self, city: CityView) -> ResourceDelta:
        damage = max(0.0, 100.0 - city.average_integrity())
        return ResourceDelta(terror=3.8 + damage / 60.0, corruption=1.9, chaos=1.8)


class RuinedCity(CityCondition):
    def __init__(self) -> None:
        super().__init__(
            key="ruined",
            label="Ruined",
            description="Continuity has become a rumor maintained by exhausted officials.",
        )

    @property
    def response_multiplier(self) -> float:
        return 0.48

    def resource_pulse(self, city: CityView) -> ResourceDelta:
        return ResourceDelta(terror=5.6, corruption=2.5, chaos=3.4)


_CONDITIONS: tuple[CityCondition, ...] = (
    StableCity(),
    StrainedCity(),
    CrisisCity(),
    RuinedCity(),
)


def condition_by_key(key: str) -> CityCondition:
    for condition in _CONDITIONS:
        if condition.key == key:
            return condition
    raise ValueError(f"Unknown city condition: {key}")


def assess_condition(city: CityView) -> CityCondition:
    integrity = city.average_integrity()
    trust = city.average_trust()
    morale = city.morale
    if integrity <= 34.0 or morale <= 27.0:
        return condition_by_key("ruined")
    if integrity <= 53.0 or trust <= 45.0 or morale <= 48.0:
        return condition_by_key("crisis")
    if integrity <= 73.0 or trust <= 65.0 or morale <= 68.0:
        return condition_by_key("strained")
    return condition_by_key("stable")
