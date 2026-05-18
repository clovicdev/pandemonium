from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Protocol

from pandemonium_modern_ruin.events import GameEvent


class ThreatStage(str, Enum):
    UNSEEN = "unseen"
    LOCAL_ALARM = "local_alarm"
    COORDINATED_RESPONSE = "coordinated_response"
    EMERGENCY_POWERS = "emergency_powers"
    OCCULT_TASK_FORCE = "occult_task_force"

    def __str__(self) -> str:
        return self.value

    @property
    def label(self) -> str:
        return {
            ThreatStage.UNSEEN: "Unseen Disturbance",
            ThreatStage.LOCAL_ALARM: "Local Alarm",
            ThreatStage.COORDINATED_RESPONSE: "Coordinated Response",
            ThreatStage.EMERGENCY_POWERS: "Emergency Powers",
            ThreatStage.OCCULT_TASK_FORCE: "Occult Task Force",
        }[self]


@dataclass(frozen=True)
class ResponsePolicy:
    repair: float
    detection: float
    possession_resistance: float
    containment: float

    @classmethod
    def for_stage(cls, stage: ThreatStage) -> ResponsePolicy:
        return {
            ThreatStage.UNSEEN: cls(repair=2.0, detection=1.5, possession_resistance=2.0, containment=0.0),
            ThreatStage.LOCAL_ALARM: cls(
                repair=3.5,
                detection=5.0,
                possession_resistance=8.0,
                containment=1.2,
            ),
            ThreatStage.COORDINATED_RESPONSE: cls(
                repair=5.4,
                detection=9.5,
                possession_resistance=17.0,
                containment=2.8,
            ),
            ThreatStage.EMERGENCY_POWERS: cls(
                repair=7.2,
                detection=15.0,
                possession_resistance=28.0,
                containment=4.7,
            ),
            ThreatStage.OCCULT_TASK_FORCE: cls(
                repair=8.5,
                detection=23.0,
                possession_resistance=42.0,
                containment=7.4,
            ),
        }[stage]


class ThreatObserver(Protocol):
    def on_stage_changed(
        self,
        previous: ThreatStage,
        current: ThreatStage,
        monitor: ThreatMonitor,
        city: object,
    ) -> None: ...


@dataclass
class ThreatMonitor:
    score: float = 0.0
    stage: ThreatStage = ThreatStage.UNSEEN
    observers: list[ThreatObserver] = field(default_factory=list, repr=False)

    def attach(self, observer: ThreatObserver) -> None:
        self.observers.append(observer)

    def ingest(self, event: GameEvent, city: object) -> None:
        self.raise_by(event.public_pressure(), city)

    def raise_by(self, amount: float, city: object) -> None:
        self.score = max(0.0, self.score + amount)
        current = stage_for_score(self.score)
        if current == self.stage:
            return
        previous = self.stage
        self.stage = current
        for observer in tuple(self.observers):
            observer.on_stage_changed(previous, current, self, city)

    def as_dict(self) -> dict[str, object]:
        return {"score": self.score, "stage": self.stage.value}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> ThreatMonitor:
        score = float(payload.get("score", 0.0))
        return cls(score=score, stage=ThreatStage(str(payload.get("stage", stage_for_score(score).value))))


class GovernmentResponseObserver:
    def on_stage_changed(
        self,
        previous: ThreatStage,
        current: ThreatStage,
        monitor: ThreatMonitor,
        city: object,
    ) -> None:
        if not hasattr(city, "response_policy") or not hasattr(city, "escalations"):
            return
        city.response_policy = ResponsePolicy.for_stage(current)
        city.escalations.append(_escalation_copy(previous, current))


def stage_for_score(score: float) -> ThreatStage:
    if score >= 118.0:
        return ThreatStage.OCCULT_TASK_FORCE
    if score >= 84.0:
        return ThreatStage.EMERGENCY_POWERS
    if score >= 52.0:
        return ThreatStage.COORDINATED_RESPONSE
    if score >= 24.0:
        return ThreatStage.LOCAL_ALARM
    return ThreatStage.UNSEEN


def _escalation_copy(previous: ThreatStage, current: ThreatStage) -> str:
    return {
        ThreatStage.LOCAL_ALARM: (
            f"{previous.label} becomes {current.label}: police commands, municipal responders, "
            "and local incident teams begin comparing notes."
        ),
        ThreatStage.COORDINATED_RESPONSE: (
            f"{previous.label} becomes {current.label}: federal analysts and private security "
            "contractors coordinate countermeasures."
        ),
        ThreatStage.EMERGENCY_POWERS: (
            f"{previous.label} becomes {current.label}: emergency authorities harden public "
            "systems and restrict compromised channels."
        ),
        ThreatStage.OCCULT_TASK_FORCE: (
            f"{previous.label} becomes {current.label}: specialized investigators stop treating "
            "the pattern as merely human."
        ),
        ThreatStage.UNSEEN: f"{previous.label} recedes into {current.label}.",
    }[current]
