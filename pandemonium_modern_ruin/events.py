from __future__ import annotations

from dataclasses import dataclass, field

from pandemonium_modern_ruin.resources import ResourceDelta


@dataclass(frozen=True)
class GameEvent:
    title: str
    detail: str
    severity: float
    visibility: float
    resource_delta: ResourceDelta = field(default_factory=ResourceDelta)
    subsystem: str | None = None
    threat_delta: float = 0.0
    tags: tuple[str, ...] = ()

    def public_pressure(self) -> float:
        return max(0.0, self.visibility * 0.55 + self.severity * 0.85 + self.threat_delta)

    def as_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "detail": self.detail,
            "severity": round(self.severity, 4),
            "visibility": round(self.visibility, 4),
            "resource_delta": self.resource_delta.values(),
            "subsystem": self.subsystem,
            "threat_delta": round(self.threat_delta, 4),
            "tags": list(self.tags),
        }


@dataclass(frozen=True)
class ActionReport:
    message: str
    events: tuple[GameEvent, ...] = ()
    success: bool = True

    @classmethod
    def failed(cls, message: str) -> ActionReport:
        return cls(message=message, events=(), success=False)
