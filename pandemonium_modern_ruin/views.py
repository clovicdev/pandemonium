from __future__ import annotations

from pandemonium_modern_ruin.abilities import AbilityRegistry
from pandemonium_modern_ruin.city import City
from pandemonium_modern_ruin.events import GameEvent
from pandemonium_modern_ruin.simulation import Simulation, TurnOutcome


class TextRenderer:
    def status(self, simulation: Simulation) -> str:
        city = simulation.city
        threat = simulation.threat
        lines = [
            f"{city.name} | Turn {city.turn} | Run {simulation.seed}",
            f"City: {city.condition.label} | Police: {threat.stage.label} ({threat.score:.1f})",
            f"Ruin: {city.ruin_score():.1f}/100 | Mood: {city.morale:.1f}/100",
            f"You have: {city.resources.as_compact_text()}",
            "",
            _table(
                ("System", "Health", "Trust", "Security", "State"),
                [
                    (
                        system.key.label,
                        f"{system.integrity:.1f}",
                        f"{system.public_trust:.1f}",
                        f"{system.security:.1f}",
                        system.status_band,
                    )
                    for system in city.subsystems.values()
                ],
            ),
        ]
        possessed = [npc for npc in city.npcs.values() if npc.possessed]
        if possessed:
            lines.extend(
                [
                    "",
                    "People under your control: "
                    + ", ".join(f"{npc.name} ({npc.key}, suspicion {npc.suspicion:.0f})" for npc in possessed),
                ]
            )
        if city.escalations:
            lines.extend(["", "Police:", city.escalations[-1]])
        return "\n".join(lines)

    def abilities(self, registry: AbilityRegistry) -> str:
        rows = []
        for ability in registry.all():
            target = "person key" if ability.target_hint else "-"
            rows.append((ability.key, ability.cost_text(), target, ability.summary))
        return _table(("Key", "Cost", "Person", "What it does"), rows)

    def npcs(self, city: City) -> str:
        rows = []
        for npc in city.npcs.values():
            influence = ", ".join(f"{key.label} x{value:.2g}" for key, value in npc.influence.items())
            state = "under control" if npc.possessed else "free"
            rows.append(
                (
                    npc.key,
                    npc.name,
                    npc.role.label,
                    state,
                    f"{npc.suspicion:.0f}",
                    str(npc.cooldown),
                    influence,
                )
            )
        return _table(("Key", "Name", "Job", "State", "Alert", "Wait", "Systems"), rows)

    def outcome(self, outcome: TurnOutcome, simulation: Simulation) -> str:
        lines = [outcome.headline]
        for escalation in outcome.escalations:
            lines.extend(["", f"Police response: {escalation}"])
        notable = [event for event in outcome.events if _is_notable(event)]
        if notable:
            lines.append("")
            for event in notable[:8]:
                lines.append(f"- {event.title}: {event.detail}{_delta_text(event)}")
        if len(notable) > 8:
            lines.append(f"- ...and {len(notable) - 8} more events.")
        lines.extend(
            [
                "",
                f"Police {simulation.threat.score:.1f} ({simulation.threat.stage.label}) | "
                f"Ruin {simulation.city.ruin_score():.1f}/100 | "
                f"{simulation.city.resources.as_compact_text()}",
            ]
        )
        if outcome.victory:
            lines.append("")
            lines.append("The city is yours. Most people had a worse night.")
        elif outcome.banished:
            lines.append("")
            lines.append("They caught you. Your run is over.")
        return "\n".join(lines)

    def help(self) -> str:
        return "\n".join(
            [
                "Try these:",
                "  status                 Show the city.",
                "  abilities              List moves and costs.",
                "  npcs                   List people and their keys.",
                "  cast <move> [person]   Use a move.",
                "  possess <person>       Take over a person.",
                "  exploit <person>       Use them to break systems.",
                "  wait                   Pass a turn.",
                "  save <path>            Save this run.",
                "  load <path>            Load a saved run.",
                "  quit                   Quit the game.",
            ]
        )


def _is_notable(event: GameEvent) -> bool:
    has_resource_change = any(abs(value) > 0.001 for value in event.resource_delta.values().values())
    return event.severity > 0.0 or event.visibility > 0.0 or has_resource_change


def _delta_text(event: GameEvent) -> str:
    positive = [
        f"+{value:.1f} {name.title()}"
        for name, value in event.resource_delta.values().items()
        if value > 0
    ]
    negative = [
        f"{value:.1f} {name.title()}"
        for name, value in event.resource_delta.values().items()
        if value < 0
    ]
    changes = positive + negative
    return f" ({', '.join(changes)})" if changes else ""


def _table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    line = " | ".join(header.ljust(widths[index]) for index, header in enumerate(headers))
    divider = "-+-".join("-" * width for width in widths)
    body = [" | ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)) for row in rows]
    return "\n".join([line, divider, *body])
