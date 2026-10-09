from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from random import Random

from pandemonium_modern_ruin.city import City
from pandemonium_modern_ruin.events import ActionReport, GameEvent
from pandemonium_modern_ruin.exceptions import AbilityNotFound, InvalidTarget
from pandemonium_modern_ruin.npcs import NPC, NPCRole
from pandemonium_modern_ruin.resources import ResourceDelta
from pandemonium_modern_ruin.subsystems import SubsystemKey
from pandemonium_modern_ruin.threat import ThreatMonitor


@dataclass
class AbilityContext:
    city: City
    threat: ThreatMonitor
    rng: Random


class AbilityCommand(ABC):
    key: str
    name: str
    summary: str
    cost: ResourceDelta
    target_hint: str | None = None

    @abstractmethod
    def execute(self, context: AbilityContext, target: str | None = None) -> ActionReport:
        raise NotImplementedError

    def cost_text(self) -> str:
        parts = []
        if self.cost.terror:
            parts.append(f"{self.cost.terror:g} Terror")
        if self.cost.corruption:
            parts.append(f"{self.cost.corruption:g} Corruption")
        if self.cost.chaos:
            parts.append(f"{self.cost.chaos:g} Chaos")
        return ", ".join(parts) if parts else "Free"


class BlackoutCascade(AbilityCommand):
    key = "blackout"
    name = "Blackout"
    summary = "Cut the power. Other systems may fail too."
    cost = ResourceDelta(corruption=2.0, chaos=5.0)

    def execute(self, context: AbilityContext, target: str | None = None) -> ActionReport:
        city = context.city
        city.resources.pay(self.cost, reason=self.name)
        amount = context.rng.uniform(16.0, 27.0) * _resistance_factor(city, SubsystemKey.POWER)
        actual = city.subsystems[SubsystemKey.POWER].damage(amount)
        comms = city.subsystems[SubsystemKey.COMMS].damage(actual * 0.18, trust_factor=0.16)
        delta = ResourceDelta(terror=6.0 + actual * 0.36, corruption=1.1, chaos=2.2 + comms * 0.08)
        city.resources.credit(delta)
        return ActionReport(
            message="The lights go out. Your slideshow can wait.",
            events=(
                GameEvent(
                    title="Blackout",
                    detail=f"Power health falls by {actual:.1f}. Phone and internet health drops by {comms:.1f}.",
                    severity=6.0 + actual / 3.4,
                    visibility=6.5 + actual / 4.0,
                    resource_delta=delta.rounded(),
                    subsystem=SubsystemKey.POWER.value,
                    threat_delta=4.5,
                    tags=("ability", "power"),
                ),
            ),
        )


class MarketPanic(AbilityCommand):
    key = "market_panic"
    name = "Market Panic"
    summary = "Rattle the markets and the city office at once."
    cost = ResourceDelta(corruption=5.0, chaos=2.0)

    def execute(self, context: AbilityContext, target: str | None = None) -> ActionReport:
        city = context.city
        city.resources.pay(self.cost, reason=self.name)
        finance_damage = context.rng.uniform(14.0, 24.0) * _resistance_factor(city, SubsystemKey.FINANCE)
        actual = city.subsystems[SubsystemKey.FINANCE].damage(finance_damage, trust_factor=0.52)
        gov = city.subsystems[SubsystemKey.GOVERNMENT].damage(actual * 0.16, trust_factor=0.22)
        delta = ResourceDelta(terror=3.5 + actual * 0.22, corruption=3.0 + actual * 0.14, chaos=1.4)
        city.resources.credit(delta)
        return ActionReport(
            message="The market panics. The anchors pretend it's fine.",
            events=(
                GameEvent(
                    title="Market panic",
                    detail=(
                        f"Market health falls by {actual:.1f}. City offices lose {gov:.1f} health."
                    ),
                    severity=5.0 + actual / 3.8,
                    visibility=7.0 + actual / 5.0,
                    resource_delta=delta.rounded(),
                    subsystem=SubsystemKey.FINANCE.value,
                    threat_delta=3.6,
                    tags=("ability", "finance"),
                ),
            ),
        )


class SignalHaunting(AbilityCommand):
    key = "signal_haunting"
    name = "Signal Haunting"
    summary = "Make the city's phones and networks act haunted."
    cost = ResourceDelta(terror=2.0, chaos=4.0)

    def execute(self, context: AbilityContext, target: str | None = None) -> ActionReport:
        city = context.city
        city.resources.pay(self.cost, reason=self.name)
        actual = city.subsystems[SubsystemKey.COMMS].damage(
            context.rng.uniform(13.0, 23.0) * _resistance_factor(city, SubsystemKey.COMMS),
            trust_factor=0.48,
        )
        compromised = city.subsystems[SubsystemKey.COMMS].compromise(context.rng.uniform(4.0, 8.0))
        city.morale = max(0.0, city.morale - actual * 0.08)
        delta = ResourceDelta(terror=4.2 + actual * 0.31, corruption=2.7 + compromised * 0.2, chaos=1.6)
        city.resources.credit(delta)
        return ActionReport(
            message="The network works. It just sends weird stuff now.",
            events=(
                GameEvent(
                    title="Signal haunting",
                    detail=(
                        f"Phone and internet health falls by {actual:.1f}. "
                        f"Security drops by {compromised:.1f}."
                    ),
                    severity=4.8 + actual / 4.0,
                    visibility=8.0 + actual / 4.2,
                    resource_delta=delta.rounded(),
                    subsystem=SubsystemKey.COMMS.value,
                    threat_delta=4.2,
                    tags=("ability", "communications"),
                ),
            ),
        )


class MiasmaOfRumors(AbilityCommand):
    key = "miasma"
    name = "Rumor Wave"
    summary = "Spread a rumor about a new outbreak."
    cost = ResourceDelta(terror=4.0, corruption=3.0)

    def execute(self, context: AbilityContext, target: str | None = None) -> ActionReport:
        city = context.city
        city.resources.pay(self.cost, reason=self.name)
        health = city.subsystems[SubsystemKey.HEALTH].damage(
            context.rng.uniform(12.0, 22.0) * _resistance_factor(city, SubsystemKey.HEALTH),
            trust_factor=0.46,
        )
        gov = city.subsystems[SubsystemKey.GOVERNMENT].damage(health * 0.20, trust_factor=0.30)
        city.morale = max(0.0, city.morale - health * 0.12)
        delta = ResourceDelta(terror=5.2 + health * 0.34, corruption=2.1, chaos=1.1 + gov * 0.08)
        city.resources.credit(delta)
        return ActionReport(
            message="People rush the hospital. Nobody trusts the all-clear.",
            events=(
                GameEvent(
                    title="Rumors spread",
                    detail=f"Hospital health falls by {health:.1f}. City offices lose {gov:.1f} health.",
                    severity=5.2 + health / 3.6,
                    visibility=6.2 + health / 4.5,
                    resource_delta=delta.rounded(),
                    subsystem=SubsystemKey.HEALTH.value,
                    threat_delta=3.9,
                    tags=("ability", "health"),
                ),
            ),
        )


class BureaucraticParalysis(AbilityCommand):
    key = "paralysis"
    name = "Office Gridlock"
    summary = "Keep city offices arguing instead of fixing things."
    cost = ResourceDelta(corruption=7.0, chaos=2.0)

    def execute(self, context: AbilityContext, target: str | None = None) -> ActionReport:
        city = context.city
        city.resources.pay(self.cost, reason=self.name)
        government = city.subsystems[SubsystemKey.GOVERNMENT]
        damage = government.damage(
            context.rng.uniform(15.0, 25.0) * _resistance_factor(city, SubsystemKey.GOVERNMENT),
            trust_factor=0.56,
        )
        compromised = government.compromise(context.rng.uniform(5.0, 9.0))
        delta = ResourceDelta(terror=2.6 + damage * 0.18, corruption=4.2 + compromised * 0.25, chaos=1.8)
        city.resources.credit(delta)
        return ActionReport(
            message="Every office has a plan. None of them match.",
            events=(
                GameEvent(
                    title="Office gridlock",
                    detail=(
                        f"City office health falls by {damage:.1f}. "
                        f"Security drops by {compromised:.1f}."
                    ),
                    severity=5.0 + damage / 3.9,
                    visibility=5.0 + damage / 5.1,
                    resource_delta=delta.rounded(),
                    subsystem=SubsystemKey.GOVERNMENT.value,
                    threat_delta=3.1,
                    tags=("ability", "government"),
                ),
            ),
        )


class InfernalSurge(AbilityCommand):
    key = "surge"
    name = "Chaos Surge"
    summary = "Trade fear and corruption for Chaos."
    cost = ResourceDelta(terror=8.0, corruption=5.0)

    def execute(self, context: AbilityContext, target: str | None = None) -> ActionReport:
        city = context.city
        city.resources.pay(self.cost, reason=self.name)
        instability = max(0.0, 100.0 - city.average_integrity()) / 100.0
        chaos_gain = 8.0 + instability * 9.0 + context.rng.uniform(0.0, 3.0)
        delta = ResourceDelta(chaos=chaos_gain)
        city.resources.credit(delta)
        return ActionReport(
            message="One bad day. Plenty of Chaos.",
            events=(
                GameEvent(
                    title="Chaos surge",
                    detail=f"Chaos rises by {chaos_gain:.1f}.",
                    severity=1.8 + chaos_gain / 8.0,
                    visibility=1.0,
                    resource_delta=delta.rounded(),
                    threat_delta=1.0,
                    tags=("ability", "economy"),
                ),
            ),
        )


class PossessCommand(AbilityCommand):
    key = "possess"
    name = "Take Over"
    summary = "Try to take over a person with power."
    cost = ResourceDelta(corruption=6.0, chaos=3.0)
    target_hint = "npc-key"

    def execute(self, context: AbilityContext, target: str | None = None) -> ActionReport:
        city = context.city
        npc = _target_npc(city, target)
        if npc.possessed:
            raise InvalidTarget(f"{npc.name} is already under your control.")
        city.resources.pay(self.cost, reason=self.name)
        chance = npc.possession_chance(
            city.resources.corruption,
            city.resources.chaos,
            city.response_policy.possession_resistance,
        )
        roll = context.rng.random()
        if roll <= chance:
            npc.mark_possessed()
            delta = ResourceDelta(corruption=1.5, chaos=0.8)
            city.resources.credit(delta)
            return ActionReport(
                message=f"{npc.name} is yours now. Their 3 p.m. meeting is still on.",
                events=(
                    GameEvent(
                        title=f"{npc.name} is under your control",
                        detail=f"{npc.role.label} taken over. Chance: {chance * 100:.0f}%." ,
                        severity=4.5,
                        visibility=1.8 + npc.suspicion / 28.0,
                        resource_delta=delta.rounded(),
                        threat_delta=2.8,
                        tags=("ability", "possession"),
                    ),
                ),
            )

        npc.suspicion = min(100.0, npc.suspicion + 18.0)
        return ActionReport(
            message=f"{npc.name} says no. They know something's wrong.",
            events=(
                GameEvent(
                    title=f"{npc.name} caught on",
                    detail=f"Chance was {chance * 100:.0f}%. The try failed.",
                    severity=2.8,
                    visibility=2.0 + npc.suspicion / 26.0,
                    threat_delta=3.2,
                    tags=("ability", "possession", "failed"),
                ),
            ),
            success=False,
        )


class ExploitPossession(AbilityCommand):
    key = "exploit"
    name = "Pull Strings"
    summary = "Use someone you took over to damage city systems."
    cost = ResourceDelta(chaos=2.0)
    target_hint = "npc-key"

    def execute(self, context: AbilityContext, target: str | None = None) -> ActionReport:
        city = context.city
        npc = _target_npc(city, target)
        if not npc.possessed:
            raise InvalidTarget(f"You haven't taken over {npc.name} yet.")
        if npc.cooldown > 0:
            raise InvalidTarget(f"Wait {npc.cooldown} more turn(s) before using {npc.name} again.")
        city.resources.pay(self.cost, reason=self.name)

        events: list[GameEvent] = []
        total_damage = 0.0
        for subsystem_key, influence in npc.influence.items():
            base = context.rng.uniform(8.5, 15.5) * influence
            actual = city.subsystems[subsystem_key].damage(
                base * _resistance_factor(city, subsystem_key),
                trust_factor=0.42,
            )
            total_damage += actual
            events.append(
                GameEvent(
                    title=f"{subsystem_key.label} takes a hit",
                    detail=f"{npc.name} cuts its health by {actual:.1f}.",
                    severity=4.2 + actual / 4.0,
                    visibility=3.0 + actual / 5.5 + npc.suspicion / 45.0,
                    subsystem=subsystem_key.value,
                    threat_delta=2.2 + actual / 9.5,
                    tags=("ability", "infiltration"),
                )
            )

        flavor = _exploit_flavor(npc)
        npc.mark_exploited()
        city.morale = max(0.0, city.morale - total_damage * 0.05)
        delta = ResourceDelta(terror=3.5 + total_damage * 0.22, corruption=2.4, chaos=2.0)
        city.resources.credit(delta)
        events.append(
            GameEvent(
                title=flavor[0],
                detail=flavor[1],
                severity=3.4,
                visibility=4.0,
                resource_delta=delta.rounded(),
                threat_delta=1.4,
                tags=("ability", "infiltration", npc.role.value),
            )
        )
        return ActionReport(
            message=f"{npc.name} uses the job to mess with city systems.",
            events=tuple(events),
        )


class AbilityRegistry:
    def __init__(self, abilities: tuple[AbilityCommand, ...] | None = None) -> None:
        catalog = abilities or (
            BlackoutCascade(),
            MarketPanic(),
            SignalHaunting(),
            MiasmaOfRumors(),
            BureaucraticParalysis(),
            InfernalSurge(),
            PossessCommand(),
            ExploitPossession(),
        )
        self._abilities = {_normalize(ability.key): ability for ability in catalog}

    def get(self, key: str) -> AbilityCommand:
        normalized = _normalize(key)
        try:
            return self._abilities[normalized]
        except KeyError as exc:
            raise AbilityNotFound(f"Don't know that move: {key}") from exc

    def all(self) -> tuple[AbilityCommand, ...]:
        return tuple(self._abilities.values())


def _target_npc(city: City, target: str | None) -> NPC:
    if not target:
        raise InvalidTarget("Add a person's key. Try 'npcs' to see the list.")
    key = _normalize(target)
    try:
        return city.npcs[key]
    except KeyError as exc:
        raise InvalidTarget(f"Can't find '{target}'. Try 'npcs' to see the keys.") from exc


def _resistance_factor(city: City, subsystem_key: SubsystemKey) -> float:
    system = city.subsystems[subsystem_key]
    response_drag = city.response_policy.containment * 0.018
    security_drag = system.security / 260.0
    return max(0.52, 1.16 - response_drag - security_drag)


def _exploit_flavor(npc: NPC) -> tuple[str, str]:
    return {
        NPCRole.TECH_CEO: (
            "Leaked CEO message",
            "One memo rattles the market.",
        ),
        NPCRole.PLANT_OPERATOR: (
            "Repair delay",
            "One switch gets flipped. The repair crew is stuck.",
        ),
        NPCRole.POLITICAL_INFLUENCER: (
            "Rumor spreads",
            "One post turns a rumor into a fight.",
        ),
        NPCRole.HOSPITAL_ADMIN: (
            "Hospital panic",
            "One bad update sends the hospital into a panic.",
        ),
        NPCRole.CENTRAL_BANKER: (
            "Bank warning",
            "One careful statement starts a loud week.",
        ),
    }[npc.role]


def _normalize(value: str) -> str:
    return value.strip().lower().replace("-", "_")
