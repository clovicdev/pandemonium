from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from pandemonium_modern_ruin.subsystems import SubsystemKey


class NPCRole(str, Enum):
    TECH_CEO = "tech_ceo"
    PLANT_OPERATOR = "plant_operator"
    POLITICAL_INFLUENCER = "political_influencer"
    HOSPITAL_ADMIN = "hospital_admin"
    CENTRAL_BANKER = "central_banker"

    def __str__(self) -> str:
        return self.value

    @property
    def label(self) -> str:
        return {
            NPCRole.TECH_CEO: "Tech boss",
            NPCRole.PLANT_OPERATOR: "Power plant worker",
            NPCRole.POLITICAL_INFLUENCER: "Public figure",
            NPCRole.HOSPITAL_ADMIN: "Hospital lead",
            NPCRole.CENTRAL_BANKER: "Banker",
        }[self]


@dataclass
class NPC:
    key: str
    name: str
    role: NPCRole
    willpower: float
    suspicion: float
    influence: dict[SubsystemKey, float]
    possessed: bool = False
    cooldown: int = 0

    def possession_chance(self, corruption: float, chaos: float, response_resistance: float) -> float:
        pressure = corruption * 0.72 + chaos * 0.42
        defense = self.willpower + self.suspicion + response_resistance + (18.0 if self.possessed else 0.0)
        return min(0.92, max(0.06, pressure / (pressure + defense + 16.0)))

    def mark_possessed(self) -> None:
        self.possessed = True
        self.suspicion = min(100.0, self.suspicion + 12.0)
        self.cooldown = 1

    def mark_exploited(self) -> None:
        self.suspicion = min(100.0, self.suspicion + 21.0)
        self.cooldown = 2

    def tick(self, detection_pressure: float) -> None:
        if self.cooldown > 0:
            self.cooldown -= 1
        if self.possessed:
            self.suspicion = min(100.0, self.suspicion + detection_pressure * 0.16)
            if self.suspicion >= 96.0:
                self.possessed = False
                self.cooldown = 3
        else:
            self.suspicion = max(0.0, self.suspicion - 1.15 + detection_pressure * 0.04)

    def as_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "name": self.name,
            "role": self.role.value,
            "willpower": self.willpower,
            "suspicion": self.suspicion,
            "influence": {key.value: value for key, value in self.influence.items()},
            "possessed": self.possessed,
            "cooldown": self.cooldown,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> NPC:
        influence_payload = payload.get("influence", {})
        if not isinstance(influence_payload, Mapping):
            influence_payload = {}
        return cls(
            key=str(payload["key"]),
            name=str(payload["name"]),
            role=NPCRole(str(payload["role"])),
            willpower=float(payload["willpower"]),
            suspicion=float(payload["suspicion"]),
            influence={SubsystemKey(str(key)): float(value) for key, value in influence_payload.items()},
            possessed=bool(payload.get("possessed", False)),
            cooldown=int(payload.get("cooldown", 0)),
        )


def default_npcs() -> dict[str, NPC]:
    roster = [
        NPC(
            key="tech_ceo",
            name="Mara Voss",
            role=NPCRole.TECH_CEO,
            willpower=54.0,
            suspicion=12.0,
            influence={SubsystemKey.COMMS: 1.35, SubsystemKey.FINANCE: 0.62},
        ),
        NPC(
            key="grid_operator",
            name="Elias Thorn",
            role=NPCRole.PLANT_OPERATOR,
            willpower=61.0,
            suspicion=9.0,
            influence={SubsystemKey.POWER: 1.42, SubsystemKey.HEALTH: 0.44},
        ),
        NPC(
            key="civic_firebrand",
            name="Lenox Vale",
            role=NPCRole.POLITICAL_INFLUENCER,
            willpower=48.0,
            suspicion=18.0,
            influence={SubsystemKey.GOVERNMENT: 1.18, SubsystemKey.COMMS: 0.86},
        ),
        NPC(
            key="hospital_admin",
            name="Dr. Selene Crowe",
            role=NPCRole.HOSPITAL_ADMIN,
            willpower=58.0,
            suspicion=7.0,
            influence={SubsystemKey.HEALTH: 1.32, SubsystemKey.GOVERNMENT: 0.41},
        ),
        NPC(
            key="central_banker",
            name="Oren Black",
            role=NPCRole.CENTRAL_BANKER,
            willpower=64.0,
            suspicion=11.0,
            influence={SubsystemKey.FINANCE: 1.45, SubsystemKey.GOVERNMENT: 0.53},
        ),
    ]
    return {npc.key: npc for npc in roster}
