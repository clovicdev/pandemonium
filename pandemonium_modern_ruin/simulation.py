from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Mapping

from pandemonium_modern_ruin.abilities import AbilityContext, AbilityRegistry
from pandemonium_modern_ruin.city import City
from pandemonium_modern_ruin.events import ActionReport, GameEvent
from pandemonium_modern_ruin.threat import GovernmentResponseObserver, ResponsePolicy, ThreatMonitor


@dataclass(frozen=True)
class TurnOutcome:
    headline: str
    events: tuple[GameEvent, ...]
    escalations: tuple[str, ...]
    victory: bool
    banished: bool
    success: bool = True


@dataclass
class Simulation:
    city: City
    threat: ThreatMonitor
    rng: Random
    seed: int
    registry: AbilityRegistry

    @classmethod
    def new(cls, *, seed: int | None = None, city_name: str = "New Carthage") -> Simulation:
        chosen_seed = seed if seed is not None else Random().randrange(1, 2**31 - 1)
        sim = cls(
            city=City(name=city_name),
            threat=ThreatMonitor(),
            rng=Random(chosen_seed),
            seed=chosen_seed,
            registry=AbilityRegistry(),
        )
        sim._wire_observers()
        return sim

    def perform_ability(self, key: str, target: str | None = None) -> TurnOutcome:
        ability = self.registry.get(key)
        before_escalations = len(self.city.escalations)
        report = ability.execute(AbilityContext(self.city, self.threat, self.rng), target)
        events = list(report.events)
        self._publish(report.events)
        tick_events = self.city.tick(self.threat.score, self.rng)
        events.extend(tick_events)
        self._publish(tick_events)
        return self._outcome(report, tuple(events), before_escalations)

    def wait(self) -> TurnOutcome:
        before_escalations = len(self.city.escalations)
        tick_events = self.city.tick(self.threat.score, self.rng)
        self._publish(tick_events)
        report = ActionReport("You let the city listen to itself for one more turn.", tick_events)
        return self._outcome(report, tick_events, before_escalations)

    def summary(self) -> dict[str, object]:
        return {
            "city": self.city.name,
            "turn": self.city.turn,
            "seed": self.seed,
            "condition": self.city.condition.label,
            "threat_stage": self.threat.stage.label,
            "threat_score": round(self.threat.score, 2),
            "ruin_score": round(self.city.ruin_score(), 2),
            "resources": self.city.resources.as_dict(),
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "version": 1,
            "seed": self.seed,
            "city": self.city.as_dict(),
            "threat": self.threat.as_dict(),
            "rng_state": _state_to_json(self.rng.getstate()),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> Simulation:
        city_payload = payload.get("city")
        threat_payload = payload.get("threat")
        if not isinstance(city_payload, Mapping) or not isinstance(threat_payload, Mapping):
            raise ValueError("Save file is missing city or threat data.")
        rng = Random()
        rng_state = payload.get("rng_state")
        if rng_state is not None:
            rng.setstate(_state_from_json(rng_state))
        else:
            rng.seed(int(payload.get("seed", 1)))
        sim = cls(
            city=City.from_mapping(city_payload),
            threat=ThreatMonitor.from_mapping(threat_payload),
            rng=rng,
            seed=int(payload.get("seed", 1)),
            registry=AbilityRegistry(),
        )
        sim._wire_observers()
        return sim

    def _wire_observers(self) -> None:
        self.threat.observers.clear()
        self.threat.attach(GovernmentResponseObserver())
        self.city.response_policy = ResponsePolicy.for_stage(self.threat.stage)

    def _publish(self, events: tuple[GameEvent, ...]) -> None:
        for event in events:
            self.city.record(event)
            if "response" in event.tags or "economy" in event.tags:
                continue
            self.threat.ingest(event, self.city)

    def _outcome(
        self,
        report: ActionReport,
        events: tuple[GameEvent, ...],
        before_escalations: int,
    ) -> TurnOutcome:
        new_escalations = tuple(self.city.escalations[before_escalations:])
        return TurnOutcome(
            headline=report.message,
            events=events,
            escalations=new_escalations,
            victory=self.city.is_ruined(),
            banished=self.city.is_banished(self.threat.score),
            success=report.success,
        )


def _state_to_json(value: object) -> object:
    if isinstance(value, tuple):
        return [_state_to_json(item) for item in value]
    if isinstance(value, list):
        return [_state_to_json(item) for item in value]
    return value


def _state_from_json(value: object) -> object:
    if isinstance(value, list):
        return tuple(_state_from_json(item) for item in value)
    return value
