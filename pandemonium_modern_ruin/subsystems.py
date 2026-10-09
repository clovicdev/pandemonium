from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class SubsystemKey(str, Enum):
    POWER = "power_grid"
    FINANCE = "financial_markets"
    COMMS = "digital_communications"
    HEALTH = "public_health"
    GOVERNMENT = "government_response"

    def __str__(self) -> str:
        return self.value

    @property
    def label(self) -> str:
        return {
            SubsystemKey.POWER: "Power",
            SubsystemKey.FINANCE: "Markets",
            SubsystemKey.COMMS: "Phones & Internet",
            SubsystemKey.HEALTH: "Hospitals",
            SubsystemKey.GOVERNMENT: "City Offices",
        }[self]


@dataclass
class Subsystem:
    key: SubsystemKey
    integrity: float
    public_trust: float
    security: float
    volatility: float
    coupling: dict[SubsystemKey, float] = field(default_factory=dict)
    strain: float = 0.0

    def damage(self, amount: float, *, trust_factor: float = 0.35) -> float:
        clean_amount = max(0.0, amount)
        previous = self.integrity
        self.integrity = _clamp(self.integrity - clean_amount)
        actual = previous - self.integrity
        self.public_trust = _clamp(self.public_trust - actual * trust_factor * self.volatility)
        self.strain = _clamp(self.strain + actual * 0.4, upper=200.0)
        return actual

    def compromise(self, amount: float) -> float:
        clean_amount = max(0.0, amount)
        previous = self.security
        self.security = _clamp(self.security - clean_amount)
        self.public_trust = _clamp(self.public_trust - clean_amount * 0.18)
        return previous - self.security

    def repair(self, amount: float) -> float:
        clean_amount = max(0.0, amount)
        if clean_amount == 0:
            return 0.0
        previous = self.integrity
        effectiveness = 0.62 + self.security / 250.0
        self.integrity = _clamp(self.integrity + clean_amount * effectiveness)
        self.public_trust = _clamp(self.public_trust + clean_amount * 0.12)
        self.strain = max(0.0, self.strain - clean_amount * 0.8)
        return self.integrity - previous

    @property
    def failure_ratio(self) -> float:
        return (100.0 - self.integrity) / 100.0

    @property
    def status_band(self) -> str:
        if self.integrity >= 76:
            return "working"
        if self.integrity >= 51:
            return "strained"
        if self.integrity >= 26:
            return "failing"
        return "collapsed"

    def as_dict(self) -> dict[str, object]:
        return {
            "key": self.key.value,
            "integrity": self.integrity,
            "public_trust": self.public_trust,
            "security": self.security,
            "volatility": self.volatility,
            "coupling": {key.value: value for key, value in self.coupling.items()},
            "strain": self.strain,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> Subsystem:
        coupling_payload = payload.get("coupling", {})
        if not isinstance(coupling_payload, Mapping):
            coupling_payload = {}
        return cls(
            key=SubsystemKey(str(payload["key"])),
            integrity=float(payload["integrity"]),
            public_trust=float(payload["public_trust"]),
            security=float(payload["security"]),
            volatility=float(payload["volatility"]),
            coupling={SubsystemKey(str(key)): float(value) for key, value in coupling_payload.items()},
            strain=float(payload.get("strain", 0.0)),
        )


def default_subsystems() -> dict[SubsystemKey, Subsystem]:
    systems = {
        SubsystemKey.POWER: Subsystem(SubsystemKey.POWER, 91.0, 84.0, 72.0, 1.12),
        SubsystemKey.FINANCE: Subsystem(SubsystemKey.FINANCE, 88.0, 79.0, 81.0, 1.28),
        SubsystemKey.COMMS: Subsystem(SubsystemKey.COMMS, 93.0, 82.0, 74.0, 1.34),
        SubsystemKey.HEALTH: Subsystem(SubsystemKey.HEALTH, 86.0, 86.0, 70.0, 1.05),
        SubsystemKey.GOVERNMENT: Subsystem(SubsystemKey.GOVERNMENT, 83.0, 72.0, 76.0, 1.18),
    }
    systems[SubsystemKey.POWER].coupling = {
        SubsystemKey.COMMS: 0.46,
        SubsystemKey.HEALTH: 0.34,
        SubsystemKey.FINANCE: 0.28,
    }
    systems[SubsystemKey.FINANCE].coupling = {
        SubsystemKey.GOVERNMENT: 0.39,
        SubsystemKey.HEALTH: 0.24,
        SubsystemKey.COMMS: 0.31,
    }
    systems[SubsystemKey.COMMS].coupling = {
        SubsystemKey.FINANCE: 0.43,
        SubsystemKey.GOVERNMENT: 0.37,
        SubsystemKey.HEALTH: 0.19,
    }
    systems[SubsystemKey.HEALTH].coupling = {
        SubsystemKey.GOVERNMENT: 0.42,
        SubsystemKey.FINANCE: 0.27,
        SubsystemKey.POWER: 0.22,
    }
    systems[SubsystemKey.GOVERNMENT].coupling = {
        SubsystemKey.POWER: 0.25,
        SubsystemKey.FINANCE: 0.32,
        SubsystemKey.COMMS: 0.38,
        SubsystemKey.HEALTH: 0.35,
    }
    return systems


def _clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return min(upper, max(lower, value))
