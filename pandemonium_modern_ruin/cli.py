from __future__ import annotations

import argparse
import cmd
import shlex
import sys
from pathlib import Path

from pandemonium_modern_ruin.controller import GameController
from pandemonium_modern_ruin.exceptions import PandemoniumError
from pandemonium_modern_ruin.views import TextRenderer


class PandemoniumShell(cmd.Cmd):
    intro = "Pandemonium: Modern Ruin. Type 'help' for commands."
    prompt = "pandemonium> "

    def __init__(self, controller: GameController, renderer: TextRenderer | None = None) -> None:
        super().__init__()
        self.controller = controller
        self.renderer = renderer or TextRenderer()

    def do_status(self, arg: str) -> None:
        print(self.renderer.status(self.controller.simulation))

    def do_abilities(self, arg: str) -> None:
        print(self.renderer.abilities(self.controller.simulation.registry))

    def do_npcs(self, arg: str) -> None:
        print(self.renderer.npcs(self.controller.simulation.city))

    def do_cast(self, arg: str) -> bool | None:
        parts = shlex.split(arg)
        if not parts:
            print("Usage: cast <ability> [target]")
            return None
        ability = parts[0]
        target = parts[1] if len(parts) > 1 else None
        return self._resolve_turn(lambda: self.controller.cast(ability, target))

    def do_possess(self, arg: str) -> bool | None:
        target = arg.strip()
        if not target:
            print("Usage: possess <npc-key>")
            return None
        return self._resolve_turn(lambda: self.controller.cast("possess", target))

    def do_exploit(self, arg: str) -> bool | None:
        target = arg.strip()
        if not target:
            print("Usage: exploit <npc-key>")
            return None
        return self._resolve_turn(lambda: self.controller.cast("exploit", target))

    def do_wait(self, arg: str) -> bool | None:
        return self._resolve_turn(self.controller.wait)

    def do_save(self, arg: str) -> None:
        destination = arg.strip() or "pandemonium-save.json"
        try:
            path = self.controller.save(destination)
        except PandemoniumError as exc:
            print(exc)
            return
        print(f"Saved to {path}")

    def do_load(self, arg: str) -> None:
        source = arg.strip()
        if not source:
            print("Usage: load <path>")
            return
        try:
            self.controller.load_into_self(source)
        except PandemoniumError as exc:
            print(exc)
            return
        print(f"Loaded {Path(source).expanduser().resolve()}")
        print(self.renderer.status(self.controller.simulation))

    def do_help(self, arg: str) -> None:
        print(self.renderer.help())

    def do_quit(self, arg: str) -> bool:
        return True

    def do_exit(self, arg: str) -> bool:
        return True

    def do_EOF(self, arg: str) -> bool:
        print()
        return True

    def emptyline(self) -> None:
        return None

    def default(self, line: str) -> None:
        print(f"Unknown command: {line}. Type 'help' for options.")

    def _resolve_turn(self, action) -> bool | None:
        try:
            outcome = action()
        except PandemoniumError as exc:
            print(exc)
            return None
        print(self.renderer.outcome(outcome, self.controller.simulation))
        return True if outcome.victory or outcome.banished else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pandemonium", description="Play Pandemonium: Modern Ruin.")
    parser.add_argument("--seed", type=int, default=None, help="Deterministic seed for a new game.")
    parser.add_argument("--city", default="New Carthage", help="City name for a new game.")
    parser.add_argument("--load", dest="load_path", default=None, help="Load a JSON save file.")
    parser.add_argument("--demo", action="store_true", help="Run a short deterministic demonstration.")
    args = parser.parse_args(argv)

    try:
        controller = (
            GameController.load(args.load_path)
            if args.load_path
            else GameController.new(seed=args.seed, city_name=args.city)
        )
    except PandemoniumError as exc:
        print(exc, file=sys.stderr)
        return 2

    renderer = TextRenderer()
    if args.demo:
        _run_demo(controller, renderer)
        return 0

    shell = PandemoniumShell(controller, renderer)
    shell.cmdloop()
    return 0


def _run_demo(controller: GameController, renderer: TextRenderer) -> None:
    print(renderer.status(controller.simulation))
    script = (
        ("signal_haunting", None),
        ("market_panic", None),
        ("possess", "tech_ceo"),
        ("blackout", None),
    )
    for ability, target in script:
        print(f"\n> cast {ability}{' ' + target if target else ''}")
        try:
            outcome = controller.cast(ability, target)
        except PandemoniumError as exc:
            print(exc)
            continue
        print(renderer.outcome(outcome, controller.simulation))
        if outcome.victory or outcome.banished:
            break


if __name__ == "__main__":
    raise SystemExit(main())
