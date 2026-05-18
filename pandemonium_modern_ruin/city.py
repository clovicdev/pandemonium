from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Mapping

from pandemonium_modern_ruin.city_state import assess_condition, condition_by_key
from pandemonium_modern_ruin.events import GameEvent
from pandemonium_modern_ruin.npcs import NPC, default_npcs
from pandemonium_modern_ruin.resources import ResourceDelta, ResourceLedger
from pandemonium_modern_ruin.subsystems import Subsystem, SubsystemKey, default_subsystems
from pandemonium_modern_ruin.threat import ResponsePolicy, ThreatStage


@dataclass
class City:
    name: str = "New Carthage"
    turn: int = 0
    morale: float = 82.0
    resources: ResourceLedger = field(default_factory=ResourceLedger)
    subsystems: dict[SubsystemKey, Subsystem] = field(default_factory=default_subsystems)
    npcs: dict[str, NPC] = field(default_factory=default_npcs)
    condition_key: str = "stable"
    response_policy: ResponsePolicy = field(
        default_factory=lambda: ResponsePolicy.for_stage(ThreatStage.UNSEEN)
    )
    escalations: list[str] = field(default_factory=list)
    chronicle: list[str] = field(default_factory=list)

    @property
    def condition(self):
        return condition_by_key(self.condition_key)

    def average_integrity(self) -> float:
        return sum(system.integrity for system in self.subsystems.values()) / len(self.subsystems)

    def average_trust(self) -> float:
        return sum(system.public_trust for system in self.subsystems.values()) / len(self.subsystems)

    def ruin_score(self) -> float:
        system_damage = 100.0 - self.average_integrity()
        trust_damage = 100.0 - self.average_trust()
        morale_damage = 100.0 - self.morale
        collapsed = sum(1 for system in self.subsystems.values() if system.integrity <= 25.0)
        return min(
            100.0,
            system_damage * 0.52 + trust_damage * 0.24 + morale_damage * 0.20 + collapsed * 4.0,
        )

    def is_ruined(self) -> bool:
        return self.ruin_score() >= 88.0 or self.average_integrity() <= 18.0 or self.morale <= 12.0

    def is_banished(self, threat_score: float) -> bool:
        pressure = self.response_policy.containment + max(0.0, threat_score - 128.0) / 9.0
        return threat_score >= 158.0 and self.resources.chaos < pressure

    def tick(self, threat_score: float, rng: Random) -> tuple[GameEvent, ...]:
        self.turn += 1
        events: list[GameEvent] = []
        previous_condition = self.condition_key
        self.condition_key = assess_condition(self).key

        pulse = self.condition.resource_pulse(self)
        self.resources.credit(pulse)
        events.append(
            GameEvent(
                title="The city's fear ferments",
                detail=f"{self.condition.label} conditions feed the infernal economy.",
                severity=0.0,
                visibility=0.0,
                resource_delta=pulse.rounded(),
                tags=("economy",),
            )
        )

        events.extend(self._cascade_failures(rng))
        events.extend(self._human_response())
        containment_event = self._containment_drain()
        if containment_event is not None:
            events.append(containment_event)

        self._move_morale(threat_score)
        detection_pressure = self.response_policy.detection + threat_score / 42.0
        for npc in self.npcs.values():
            npc.tick(detection_pressure)

        self.condition_key = assess_condition(self).key
        if self.condition_key != previous_condition:
            condition = self.condition
            events.append(
                GameEvent(
                    title=f"City condition: {condition.label}",
                    detail=condition.description,
                    severity=2.0,
                    visibility=1.2,
                    threat_delta=0.4,
                    tags=("city_state",),
                )
            )

        self._trim_chronicle()
        return tuple(events)

    def record(self, event: GameEvent) -> None:
        self.chronicle.append(f"Turn {self.turn}: {event.title} - {event.detail}")
        self._trim_chronicle()

    def _cascade_failures(self, rng: Random) -> tuple[GameEvent, ...]:
        cascades: list[GameEvent] = []
        for source in tuple(self.subsystems.values()):
            if source.failure_ratio < 0.24:
                continue
            for target_key, coupling in source.coupling.items():
                target = self.subsystems[target_key]
                if target.integrity <= 0.0:
                    continue
                pressure = source.failure_ratio * coupling * source.volatility * (0.88 + source.strain / 150.0)
                if rng.random() > min(0.82, pressure):
                    continue
                amount = rng.uniform(0.8, 3.9) * (1.0 + pressure * 2.1)
                actual = target.damage(amount, trust_factor=0.18)
                if actual < 0.45:
                    continue
                delta = ResourceDelta(terror=actual * 0.18, corruption=actual * 0.06, chaos=actual * 0.08)
                self.resources.credit(delta)
                cascades.append(
                    GameEvent(
                        title=f"{source.key.label} cascade hits {target.key.label}",
                        detail=(
                            f"Stress transfers through civic dependencies, cutting "
                            f"{target.key.label} integrity by {actual:.1f}."
                        ),
                        severity=actual / 3.2,
                        visibility=actual / 2.7,
                        resource_delta=delta.rounded(),
                        subsystem=target.key.value,
                        threat_delta=actual / 8.5,
                        tags=("cascade",),
                    )
                )
        return tuple(cascades)

    def _human_response(self) -> tuple[GameEvent, ...]:
        government = self.subsystems[SubsystemKey.GOVERNMENT]
        if self.response_policy.repair <= 0.0:
            return ()
        events: list[GameEvent] = []
        legitimacy = max(0.22, (government.integrity + government.public_trust) / 200.0)
        repair_budget = self.response_policy.repair * self.condition.response_multiplier * legitimacy
        damaged = sorted(self.subsystems.values(), key=lambda system: system.integrity)
        for index, system in enumerate(damaged[:3], start=1):
            if system.integrity >= 95.0:
                continue
            repaired = system.repair(repair_budget / index)
            if repaired < 0.45:
                continue
            events.append(
                GameEvent(
                    title=f"Human response stabilizes {system.key.label}",
                    detail=f"Emergency work restores {repaired:.1f} integrity.",
                    severity=0.0,
                    visibility=0.25,
                    subsystem=system.key.value,
                    tags=("response",),
                )
            )
        return tuple(events)

    def _containment_drain(self) -> GameEvent | None:
        if self.response_policy.containment <= 0.0:
            return None
        drain = ResourceDelta(
            terror=-self.response_policy.containment * 0.08,
            corruption=-self.response_policy.containment * 0.16,
            chaos=-self.response_policy.containment * 0.22,
        )
        before = self.resources.as_dict()
        self.resources.credit(drain)
        after = self.resources.as_dict()
        if before == after:
            return None
        return GameEvent(
            title="Counter-ritual pressure",
            detail="Escalated responders suppress ambient dread and disrupt infernal momentum.",
            severity=0.0,
            visibility=0.0,
            resource_delta=drain.rounded(),
            tags=("response", "containment"),
        )

    def _move_morale(self, threat_score: float) -> None:
        integrity_gap = max(0.0, 72.0 - self.average_integrity()) / 30.0
        trust_gap = max(0.0, 70.0 - self.average_trust()) / 42.0
        pressure = integrity_gap + trust_gap + threat_score / 1050.0
        recovery = 0.18 if self.average_integrity() > 78.0 and self.average_trust() > 70.0 else 0.0
        self.morale = min(100.0, max(0.0, self.morale - pressure + recovery))

    def _trim_chronicle(self) -> None:
        if len(self.chronicle) > 80:
            del self.chronicle[:-80]
        if len(self.escalations) > 20:
            del self.escalations[:-20]

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "turn": self.turn,
            "morale": self.morale,
            "resources": self.resources.as_dict(),
            "subsystems": {key.value: system.as_dict() for key, system in self.subsystems.items()},
            "npcs": {key: npc.as_dict() for key, npc in self.npcs.items()},
            "condition_key": self.condition_key,
            "response_policy": {
                "repair": self.response_policy.repair,
                "detection": self.response_policy.detection,
                "possession_resistance": self.response_policy.possession_resistance,
                "containment": self.response_policy.containment,
            },
            "escalations": list(self.escalations),
            "chronicle": list(self.chronicle),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> City:
        subsystems_payload = payload.get("subsystems", {})
        npcs_payload = payload.get("npcs", {})
        if not isinstance(subsystems_payload, Mapping) or not isinstance(npcs_payload, Mapping):
            raise ValueError("Save file has malformed city data.")
        loaded_subsystems = {
            SubsystemKey(str(key)): Subsystem.from_mapping(_mapping(value))
            for key, value in subsystems_payload.items()
        }
        canonical_subsystems = default_subsystems()
        for key, system in loaded_subsystems.items():
            canonical_coupling = canonical_subsystems[key].coupling
            system.coupling = {
                target: system.coupling[target]
                for target in canonical_coupling
                if target in system.coupling
            }
        loaded_npcs = {
            str(key): NPC.from_mapping(_mapping(value))
            for key, value in npcs_payload.items()
        }
        city = cls(
            name=str(payload.get("name", "New Carthage")),
            turn=int(payload.get("turn", 0)),
            morale=float(payload.get("morale", 82.0)),
            resources=ResourceLedger.from_mapping(_mapping(payload.get("resources", {}))),
            subsystems={key: loaded_subsystems[key] for key in SubsystemKey if key in loaded_subsystems},
            npcs={key: loaded_npcs[key] for key in default_npcs() if key in loaded_npcs},
            condition_key=str(payload.get("condition_key", "stable")),
            escalations=[str(item) for item in payload.get("escalations", [])],
            chronicle=[str(item) for item in payload.get("chronicle", [])],
        )
        policy_payload = payload.get("response_policy")
        if isinstance(policy_payload, Mapping):
            city.response_policy = ResponsePolicy(
                repair=float(policy_payload.get("repair", city.response_policy.repair)),
                detection=float(policy_payload.get("detection", city.response_policy.detection)),
                possession_resistance=float(
                    policy_payload.get(
                        "possession_resistance",
                        city.response_policy.possession_resistance,
                    )
                ),
                containment=float(policy_payload.get("containment", city.response_policy.containment)),
            )
        city.condition_key = assess_condition(city).key
        return city


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("Expected object mapping in save file.")
    return value
