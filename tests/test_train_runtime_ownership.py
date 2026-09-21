"""Exercise the actual legacy retry guard after a stand-mode login."""
import ast
import time
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "app/src/main/python/train_bot/run_party_digioi.py"


class TrainRuntimeOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.tree = ast.parse(SOURCE.read_text())
        helper = next(n for n in self.tree.body if isinstance(n, ast.FunctionDef)
                      and n.name == "_legacy_party_train_enabled")
        self.ns = {}
        exec(compile(ast.Module(body=[helper], type_ignores=[]), str(SOURCE), "exec"), self.ns)

    def test_gui_farm_never_enters_native_retry_without_startup_closure(self):
        retry = next(n for n in ast.walk(self.tree) if isinstance(n, ast.If)
                     and "last_retry" in ast.unparse(n.test)
                     and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                             and c.func.id == "_start_training" for c in ast.walk(n)))
        for phase in ("gather", "party", "route", "farming", "blocked"):
            with self.subTest(phase=phase):
                ns = dict(self.ns, st={"ui_train_target": (23803, 550, 590),
                                      "ui_train_phase": phase},
                          has_leader=True, time=time, last_retry=0)
                exec(compile(ast.Module(body=[retry], type_ignores=[]), str(SOURCE), "exec"), ns)
                self.assertEqual(ns["last_retry"], 0)

    def test_gui_farm_does_not_enable_native_flee_when_roster_is_missing(self):
        lost = next(n for n in ast.walk(self.tree) if isinstance(n, ast.If)
                    and "_legacy_party_train_enabled" in ast.unparse(n.test)
                    and "train_on_map" in ast.unparse(n.test))
        ns = dict(self.ns, st={"ui_train_target": (23803, 550, 590), "n_members": 4},
                  train_on_map=True)
        exec(compile(ast.Module(body=[lost], type_ignores=[]), str(SOURCE), "exec"), ns)

    def test_native_modes_remain_enabled_and_daily_is_separate(self):
        enabled = self.ns["_legacy_party_train_enabled"]
        self.assertTrue(enabled({}))
        self.assertTrue(enabled({"ui_train_target": None, "daily_active": False}))
        self.assertFalse(enabled({"daily_active": True}))
        self.assertFalse(enabled({"train_channel_regroup": {"phase": "safe"}}))

    def test_digioi_handoff_contains_no_daily_boss_or_dungeon_execution(self):
        source = SOURCE.read_text()
        start = source.index("        def _finish_digioi_train_after_dg():")
        end = source.index("\n        def _finish_digioi_train_if_time_over", start)
        handoff = source[start:end]
        for forbidden in ("_maybe_auto_world_boss(", "_run_auto_team_dungeons_if_needed(",
                          "do_daily_dungeon(", "claim_daily_quests(", "do_legion_boss("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, handoff)
        self.assertIn("ban giao THANG sang TRAIN", handoff)

    def test_train_and_digioi_force_daily_automation_off(self):
        source = SOURCE.read_text()
        self.assertIn('_workflow_kind in ("train", "digioi")', source)
        self.assertIn('pcfg.get("mode") in ("train", "digioi", "digioi_train")', source)
        self.assertIn('pcfg = dict(pcfg, do_daily=False, auto_world_boss=False,', source)
        self.assertIn('auto_team_dungeon=False, fight_legion_boss=False)', source)

    def test_world_boss_has_no_legacy_automatic_entry_or_shared_barrier(self):
        source = SOURCE.read_text()
        for forbidden in ("def _maybe_auto_world_boss", "_maybe_auto_world_boss(",
                          "wb_done", "def _wait_party_world_boss", "WB_WAIT_SEC"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)
        self.assertIn("from .workflows.boss import run_selected as run_daily_boss", source)
        self.assertIn("_boss_result = run_daily_boss(", source)


if __name__ == "__main__":
    unittest.main()
