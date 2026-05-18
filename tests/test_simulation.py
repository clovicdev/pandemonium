from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pandemonium_modern_ruin import Simulation
from pandemonium_modern_ruin.exceptions import AbilityNotFound
from pandemonium_modern_ruin.persistence import load_game, save_game
from pandemonium_modern_ruin.subsystems import SubsystemKey
from pandemonium_modern_ruin.threat import ThreatStage


class SimulationTests(unittest.TestCase):
    def test_blackout_advances_turn_and_damages_power(self) -> None:
        sim = Simulation.new(seed=7)
        before_power = sim.city.subsystems[SubsystemKey.POWER].integrity

        outcome = sim.perform_ability("blackout")

        self.assertTrue(outcome.success)
        self.assertEqual(sim.city.turn, 1)
        self.assertLess(sim.city.subsystems[SubsystemKey.POWER].integrity, before_power)
        self.assertGreaterEqual(sim.city.resources.terror, 0)
        self.assertGreaterEqual(sim.city.resources.corruption, 0)
        self.assertGreaterEqual(sim.city.resources.chaos, 0)

    def test_possession_then_exploit_changes_influenced_systems(self) -> None:
        sim = Simulation.new(seed=1)
        sim.city.resources.corruption = 200
        sim.city.resources.chaos = 200

        possession = sim.perform_ability("possess", "tech_ceo")
        before_comms = sim.city.subsystems[SubsystemKey.COMMS].integrity
        exploit = sim.perform_ability("exploit", "tech_ceo")

        self.assertTrue(possession.success)
        self.assertTrue(exploit.success)
        self.assertTrue(sim.city.npcs["tech_ceo"].possessed)
        self.assertLess(sim.city.subsystems[SubsystemKey.COMMS].integrity, before_comms)

    def test_save_load_preserves_rng_state(self) -> None:
        with TemporaryDirectory() as directory:
            first = Simulation.new(seed=44)
            first.perform_ability("signal_haunting")
            save_path = save_game(first, Path(directory) / "save.json")
            loaded = load_game(save_path)

            first.perform_ability("market_panic")
            loaded.perform_ability("market_panic")

            self.assertEqual(loaded.summary(), first.summary())

    def test_threat_observer_updates_response_policy(self) -> None:
        sim = Simulation.new(seed=3)

        sim.threat.raise_by(60, sim.city)

        self.assertIs(sim.threat.stage, ThreatStage.COORDINATED_RESPONSE)
        self.assertGreater(sim.city.response_policy.repair, 5)
        self.assertTrue(sim.city.escalations)

    def test_unknown_ability_is_rejected(self) -> None:
        sim = Simulation.new(seed=3)

        with self.assertRaisesRegex(AbilityNotFound, "moonfall"):
            sim.perform_ability("moonfall")


if __name__ == "__main__":
    unittest.main()
