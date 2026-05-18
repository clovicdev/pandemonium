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
    name = "Blackout Cascade"
    summary = "Overloads civic dependence on power and lets secondary failures bloom."
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
            message="A district-wide dependency chain snaps under impossible timing.",
            events=(
                GameEvent(
                    title="Blackout cascade",
                    detail=f"Power Grid integrity falls by {actual:.1f}; communications lose {comms:.1f}.",
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
    summary = "Turns confidence into contagion across financial and government systems."
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
            message="Screens glow red, anchors stumble, and institutions begin correcting each other.",
            events=(
                GameEvent(
                    title="Market panic",
                    detail=(
                        f"Financial Markets integrity falls by {actual:.1f}; "
                        f"Government Response loses {gov:.1f}."
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
    summary = "Poisons the public channel with impossible coincidences and recursive dread."
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
            message="The network remains online, which makes the haunting worse.",
            events=(
                GameEvent(
                    title="Signal haunting",
                    detail=(
                        f"Digital Communications integrity falls by {actual:.1f}; "
                        f"security slips by {compromised:.1f}."
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
    name = "Miasma of Rumors"
    summary = "Transforms ordinary symptoms and civic uncertainty into public-health dread."
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
            message="Queues lengthen, denials multiply, and rumor becomes its own weather.",
            events=(
                GameEvent(
                    title="Miasma of rumors",
                    detail=f"Public Health integrity falls by {health:.1f}; governance loses {gov:.1f}.",
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
    name = "Bureaucratic Paralysis"
    summary = "Binds agencies in contradiction, slowing repairs and raising institutional distrust."
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
            message="Every urgent memo contradicts the one before it.",
            events=(
                GameEvent(
                    title="Bureaucratic paralysis",
                    detail=(
                        f"Government Response integrity falls by {damage:.1f}; "
                        f"security loses {compromised:.1f}."
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
    name = "Infernal Surge"
    summary = "Converts accumulated fear and influence into raw Chaos Energy."
    cost = ResourceDelta(terror=8.0, corruption=5.0)

    def execute(self, context: AbilityContext, target: str | None = None) -> ActionReport:
        city = context.city
        city.resources.pay(self.cost, reason=self.name)
        instability = max(0.0, 100.0 - city.average_integrity()) / 100.0
        chaos_gain = 8.0 + instability * 9.0 + context.rng.uniform(0.0, 3.0)
        delta = ResourceDelta(chaos=chaos_gain)
        city.resources.credit(delta)
        return ActionReport(
            message="The ruin already sown is rendered into a hotter currency.",
            events=(
                GameEvent(
                    title="Infernal surge",
                    detail=f"Chaos Energy rises by {chaos_gain:.1f}.",
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
    name = "Possess Key Human"
    summary = "Attempts to seize a high-influence NPC for later systemic sabotage."
    cost = ResourceDelta(corruption=6.0, chaos=3.0)
    target_hint = "npc-key"

    def execute(self, context: AbilityContext, target: str | None = None) -> ActionReport:
        city = context.city
        npc = _target_npc(city, target)
        if npc.possessed:
            raise InvalidTarget(f"{npc.name} is already possessed.")
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
                message=f"{npc.name} opens the door from the inside.",
                events=(
                    GameEvent(
                        title=f"Possession: {npc.name}",
                        detail=(
                            f"{npc.role.label} compromised "
                            f"({chance * 100:.0f}% chance, rolled {roll * 100:.0f}%)."
                        ),
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
            message=f"{npc.name} resists and starts noticing the shape of the attempt.",
            events=(
                GameEvent(
                    title=f"Failed possession: {npc.name}",
                    detail=f"The attempt fails ({chance * 100:.0f}% chance, rolled {roll * 100:.0f}%).",
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
    name = "Exploit Possession"
    summary = "Uses a possessed NPC's authority to trigger cross-system failure from within."
    cost = ResourceDelta(chaos=2.0)
    target_hint = "npc-key"

    def execute(self, context: AbilityContext, target: str | None = None) -> ActionReport:
        city = context.city
        npc = _target_npc(city, target)
        if not npc.possessed:
            raise InvalidTarget(f"{npc.name} is not possessed.")
        if npc.cooldown > 0:
            raise InvalidTarget(f"{npc.name} needs {npc.cooldown} more turn(s) before another exploit.")
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
                    title=f"{npc.role.label} exploit hits {subsystem_key.label}",
                    detail=f"{npc.name}'s authority cuts integrity by {actual:.1f}.",
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
            message=f"{npc.name} weaponizes legitimacy without ever raising their voice.",
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
            raise AbilityNotFound(f"Unknown ability: {key}") from exc

    def all(self) -> tuple[AbilityCommand, ...]:
        return tuple(self._abilities.values())


def _target_npc(city: City, target: str | None) -> NPC:
    if not target:
        raise InvalidTarget("This ability requires an NPC key.")
    key = _normalize(target)
    try:
        return city.npcs[key]
    except KeyError as exc:
        available = ", ".join(sorted(city.npcs))
        raise InvalidTarget(f"Unknown NPC '{target}'. Available targets: {available}.") from exc


def _resistance_factor(city: City, subsystem_key: SubsystemKey) -> float:
    system = city.subsystems[subsystem_key]
    response_drag = city.response_policy.containment * 0.018
    security_drag = system.security / 260.0
    return max(0.52, 1.16 - response_drag - security_drag)


def _exploit_flavor(npc: NPC) -> tuple[str, str]:
    return {
        NPCRole.TECH_CEO: (
            "Platform consensus fracture",
            "A trusted executive message shifts millions of private assumptions at once.",
        ),
        NPCRole.PLANT_OPERATOR: (
            "Operations handoff spiral",
            "Routine authority turns minor maintenance ambiguity into cascading institutional delay.",
        ),
        NPCRole.POLITICAL_INFLUENCER: (
            "Civic legitimacy shock",
            "Followers receive certainty; everyone else receives consequences.",
        ),
        NPCRole.HOSPITAL_ADMIN: (
            "Triage rumor storm",
            "Scarce capacity and contradictory reassurance amplify each other.",
        ),
        NPCRole.CENTRAL_BANKER: (
            "Liquidity omen",
            "A careful statement is heard as prophecy, accusation, and retreat.",
        ),
    }[npc.role]


def _normalize(value: str) -> str:
    return value.strip().lower().replace("-", "_")
