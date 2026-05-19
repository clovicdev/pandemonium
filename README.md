# Pandemonium: Modern Ruin 🔥

**Pandemonium: Modern Ruin** is a deterministic Python 3.9+ command-line sandbox simulation about systemic collapse, possession, and escalating response in a fictional modern metropolis.

You play as a high-ranking demon cultivating **Terror**, **Corruption**, and **Chaos Energy** while pushing interconnected civic systems past their limits. Direct destruction is expensive and visible; infiltration is subtler, riskier, and often more devastating.

> The simulation is intentionally abstract and fictional. It models game-state pressure, trust erosion, and cascading dependencies without providing real-world procedural guidance.

## Features ✨

- **Sin economy:** Terror, Corruption, and Chaos Energy fuel different styles of ruin.
- **Dynamic city engine:** Power, finance, communications, public health, and government response are coupled systems with integrity, trust, security, volatility, and cascading failure.
- **Threat escalation:** Human awareness advances from local alarm to coordinated response, emergency powers, and occult task forces.
- **Possession matrix:** Compromise key NPCs such as a tech CEO, plant operator, political influencer, hospital administrator, or central banker.
- **Emergent turns:** Every action advances the city clock, allowing repairs, countermeasures, suspicion, morale shifts, and subsystem cascades.
- **Deterministic seeds:** Reproduce runs exactly for testing, balancing, streaming, or tournament scenarios.
- **Save/load:** JSON save files preserve city state, threat state, resources, NPCs, and RNG state.
- **Zero runtime dependencies:** Python standard library only.

## Quick Start 🚀

Open the browser terminal:

```bash
python3 -m http.server 4173
```

Then visit:

```text
http://localhost:4173
```

The static terminal app can also be served directly by GitHub Pages from the repository root.

Run the Python CLI:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pandemonium --seed 666
```

Run without installing:

```bash
python -m pandemonium_modern_ruin --seed 666
```

Try a short scripted sample:

```bash
python -m pandemonium_modern_ruin --seed 666 --demo
```

## Core Commands 🎮

The browser terminal and Python CLI share the same command vocabulary:

```text
status                 Show city, resources, threat, and subsystem health.
abilities              List demonic commands and costs.
npcs                   List possession targets and influence vectors.
cast <ability> [target] Execute an ability.
possess <npc-key>      Shortcut for cast possess <npc-key>.
exploit <npc-key>      Shortcut for cast exploit <npc-key>.
wait                   Pass one turn and let the city evolve.
save <path>            Write a JSON save file.
load <path>            Load a JSON save file.
quit                   Leave the simulation.
```

Example opening:

```text
pandemonium> abilities
pandemonium> cast signal_haunting
pandemonium> cast market_panic
pandemonium> possess tech_ceo
pandemonium> exploit tech_ceo
pandemonium> status
```

## Architecture 🏗️

The codebase is organized around a clean separation of concerns:

- `index.html` and `assets/` provide a static GitHub Pages terminal edition that mirrors the CLI game loop in the browser.
- `pandemonium_modern_ruin.city` owns the city aggregate, turn advancement, morale, cascades, response, and ruin checks.
- `pandemonium_modern_ruin.subsystems` models civic infrastructure nodes and their coupling graph.
- `pandemonium_modern_ruin.resources` defines the sin economy ledger.
- `pandemonium_modern_ruin.npcs` models possession targets, suspicion, cooldowns, and influence vectors.
- `pandemonium_modern_ruin.abilities` implements the **Command Pattern** for demonic actions.
- `pandemonium_modern_ruin.city_state` implements the **State Pattern** for Stable, Strained, Crisis, and Ruined city conditions.
- `pandemonium_modern_ruin.threat` implements the **Observer Pattern** for threat escalation and response policy changes.
- `pandemonium_modern_ruin.simulation` coordinates the domain model, RNG, event publication, and turn outcomes.
- `pandemonium_modern_ruin.controller` exposes application actions for the CLI.
- `pandemonium_modern_ruin.views` formats terminal output.
- `pandemonium_modern_ruin.persistence` handles versioned JSON save/load.
- `pandemonium_modern_ruin.cli` provides the interactive shell and demo mode.

## Design Notes 🧠

The game rewards timing and restraint. Highly visible abilities generate resources quickly but accelerate threat escalation. Possession costs more setup, yet a well-timed exploit can hit multiple systems through trusted authority. Government response grows stronger as threat rises, but damaged institutions repair less efficiently and become more vulnerable to cascading failure.

Victory arrives when the city’s ruin score crosses the domination threshold. Defeat can occur if containment pressure rises while your Chaos Energy is too low to maintain infernal presence.

## Development 🛠️

Run tests:

```bash
python -m unittest discover -s tests -v
```

Or, after installing the development extras:

```bash
python -m pytest
```

Run linting:

```bash
python -m ruff check .
```

Build a source distribution:

```bash
python -m build
```

## Save Files 💾

```text
pandemonium> save saves/night-one.json
pandemonium> load saves/night-one.json
```

You can also launch directly from a save:

```bash
pandemonium --load saves/night-one.json
```
