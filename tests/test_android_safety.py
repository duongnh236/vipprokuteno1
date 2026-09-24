"""Dependency-free regression checks for Android orchestration changes."""
import ast
import json
import logging
import sys
import threading
import time
import unittest
from collections import deque
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1] / "app/src/main/python"
sys.path.insert(0, str(ROOT))


def function(path, name, namespace):
    namespace.setdefault("__package__", "train_bot")
    namespace.setdefault("_workflow_services", lambda: SimpleNamespace(**namespace))
    tree = ast.parse((ROOT / path).read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
    return namespace[name]


def methods(path, class_name, names, namespace):
    """Extract methods of a class (no imports needed) for behavior tests."""
    tree = ast.parse((ROOT / path).read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    nodes = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return [namespace[name] for name in names]


class SafetyTests(unittest.TestCase):
    def test_kick_42_and_47_are_reconnectable_but_maintenance_is_not(self):
        source = (ROOT / "train_bot/client.py").read_text()
        self.assertIn("DISCONNECT_RECONNECTABLE = frozenset((42, 47))", source)
        self.assertIn('42: "sua goi chien dau"', source)
        self.assertIn('47: "ket thuc su kien khi tran chua ket thuc"', source)
        self.assertNotIn("frozenset((42, 47, 60))", source)

    def test_member_catches_up_at_safe_then_leader_picks_up_without_team_restart(self):
        cfg = SimpleNamespace(PARTY_LEADER_ACC={0: "leader"}, TRAIN_MAPS={23803: {"safe": [(230, 310)]}})
        st = {"lock": threading.RLock(), "cmd_gen": 8, "cmd": ("train",),
              "ui_train_target": (23803, 550, 590), "ui_train_phase": "farming",
              "ui_member_recover": {"member"}}
        leader = SimpleNamespace(running=True, current_map=23803, current_channel=11,
            pos=(550, 590), party_members=[], navigate_to=Mock(return_value=True),
            set_party_strategist=Mock())
        member = SimpleNamespace(running=True, current_map=23802, current_channel=11,
            self_entity=b"member", combat_ready=Mock(), set_party_invite_ready=Mock(),
            navigate_to=Mock(return_value=True))
        def route(*a, **kw):
            member.current_map = 23803
            return True
        member.follow_smart_route = Mock(side_effect=route)
        leader.invite_members = Mock(side_effect=lambda **kw: leader.party_members.append(b"member"))
        restart = Mock()
        ns = {"config": cfg, "account_clients": {"leader": leader, "member": member},
              "_workflow_leave_current_area": Mock(), "_nearest_safe": lambda p, points: points[0],
              "set_account_activity": Mock(), "party_train_map": restart}
        fn = function("train_bot/run_party_digioi.py", "_android_train_recovery_tick", ns)
        self.assertTrue(fn(member, st, "member", 0, lambda: False))
        member.follow_smart_route.assert_called_once()
        member.navigate_to.assert_called_once()
        leader.navigate_to.assert_not_called()
        self.assertTrue(fn(leader, st, "leader", 0, lambda: False))
        self.assertEqual([call.args for call in leader.navigate_to.call_args_list], [(230, 310), (550, 590)])
        self.assertFalse(st["ui_member_recover"])
        self.assertEqual(st["cmd_gen"], 8)
        restart.assert_not_called()

    def test_leader_loss_returns_members_to_city_before_restart(self):
        st = {"lock": threading.RLock(), "cmd_gen": 8, "cmd": ("train",),
              "ui_train_target": (23803, 550, 590), "ui_leader_recover": True,
              "manual_train_users": ["leader", "member"]}
        c = SimpleNamespace(running=True, current_map=23803,
                            nearest_smart_city=Mock(return_value=(23001, 17)))
        c.go_to_town = Mock(side_effect=lambda *a, **kw: setattr(c, "current_map", 23001))
        leader = SimpleNamespace(running=True)
        restart = Mock()
        ns = {"config": SimpleNamespace(PARTY_LEADER_ACC={0: "leader"}),
              "account_clients": {"leader": leader, "member": c},
              "_nearest_safe": Mock(),
              "_workflow_leave_current_area": Mock(), "set_account_activity": Mock(),
              "party_train_map": restart}
        fn = function("train_bot/run_party_digioi.py", "_android_train_recovery_tick", ns)
        self.assertTrue(fn(c, st, "member", 0, lambda: False))
        restart.assert_not_called()
        self.assertTrue(fn(leader, st, "leader", 0, lambda: False))
        restart.assert_called_once_with(0, 23803, 550, 590)
        self.assertFalse(st["ui_leader_recover"])

    def test_farming_channel_change_queues_safe_flow_not_direct_switch(self):
        safe = Mock()
        fn = function("train_bot/run_party_digioi.py", "_dieu_phoi_thi_hanh_kenh",
                      {"party_switch_channel": safe})
        c = SimpleNamespace(current_map=23803, current_channel=11, switch_channel=Mock())
        st = {"cmd": ("train",), "ui_train_phase": "farming", "train_channel_map": 23803}
        self.assertEqual(fn(0, st, [("leader", c)], 2), 0)
        safe.assert_called_once_with(0, 2)
        c.switch_channel.assert_not_called()
        safe.reset_mock()
        st["cmd"] = ("channel", 2)
        self.assertEqual(fn(0, st, [("leader", c)], 2), 0)
        safe.assert_not_called()

    def test_farm_map_replaces_city_pin_without_leaving_party(self):
        fn = function("train_bot/run_party_digioi.py", "_train_adopt_map_channel", {})
        st = {"lock": threading.RLock(), "cmd_gen": 3, "train_channel_map": 23001,
              "train_channel_manual": 2, "kenh_ghim": 2, "kenh_dich": 2,
              "manual_train_full": (3, 2)}
        self.assertTrue(fn(st, 23803, 11, 3))
        self.assertEqual(st["train_channel_manual"], 11)
        self.assertEqual(st["train_channel_map"], 23803)
        self.assertIsNone(st["kenh_ghim"])
        self.assertIsNone(st["kenh_dich"])
        self.assertFalse(fn(st, 23803, 2, 3))
        self.assertEqual(st["train_channel_manual"], 11)
        self.assertFalse(fn(st, 23001, 2, 2))
        self.assertEqual(st["train_channel_map"], 23803)

    def test_full_channel_fallback_requires_fresh_capacity_for_entire_team(self):
        c = SimpleNamespace(current_map=23001, current_channel=2, running=True,
            _ds_kenh_map=23001, _chan_event=Mock(), request_channel_list=Mock(),
            channels={2: (100, 100), 3: (98, 100), 4: (94, 100)})
        c._chan_event.wait.return_value = True
        clients = {"leader": c}
        for i in range(4):
            clients[str(i)] = SimpleNamespace(running=True, current_map=23001, current_channel=2)
        st = {"cmd_gen": 8, "lock": threading.RLock(), "manual_train_full": (8, 2),
              "manual_train_channel_ready": threading.Event()}
        ns = {"log": logging.getLogger("test"), "time": SimpleNamespace(time=lambda: 100),
              "account_clients": clients}
        fn = function("train_bot/run_party_digioi.py", "_train_fallback_full_channel", ns)
        cmd = ("train", 23803, 550, 590)
        self.assertTrue(fn(c, st, list(clients), cmd, 8, "leader"))
        self.assertEqual(st["manual_train_fallback"], (9, 23001, 4))
        self.assertEqual(st["cmd"], cmd)
        self.assertEqual(st["ui_train_dispatch_gen"], 9)
        self.assertTrue(c.running)
        st.update(cmd_gen=10, manual_train_full=(10, 2), manual_train_capacity_scan=0)
        c._chan_event.wait.return_value = False
        self.assertFalse(fn(c, st, list(clients), cmd, 10, "leader"))
        self.assertEqual(st["cmd_gen"], 10)

    def test_watcher_does_not_reform_during_train_gather(self):
        task = Mock(side_effect=AssertionError("Watcher must not inspect/reform owned train"))
        ns = {"_pstate": lambda p: {"ui_train_dispatch_gen": 8, "cmd_gen": 8,
                                    "ui_train_phase": "gather"},
              "time": SimpleNamespace(sleep=Mock()), "WATCH_EVERY_SEC": 20,
              "party_accounts": lambda p: [("member", None, None, None)],
              "is_account_running": Mock(side_effect=[True, False]),
              "get_account_task": task}
        fn = function("train_bot/run_party_digioi.py", "_party_watcher", ns)
        fn(0)
        task.assert_not_called()

    def test_train_channel_full_requests_safe_regroup_without_relogin(self):
        ns = {"log": logging.getLogger("test"), "time": SimpleNamespace(sleep=Mock()),
              "set_account_activity": Mock()}
        fn = function("train_bot/run_party_digioi.py", "_train_retry_leader_channel", ns)
        st = {"cmd_gen": 8, "manual_train_channel": 2, "lock": threading.RLock()}
        c = SimpleNamespace(running=True, current_channel=1, _chan_switch_result=4)
        attempts = []
        def switch(channel, **kw):
            attempts.append(channel)
            if len(attempts) == 3:
                c.current_channel = channel
                return True
            return False
        c.switch_channel = switch
        self.assertFalse(fn(c, st, "member", "member", 8, lambda: False))
        self.assertEqual(attempts, [2])
        self.assertEqual(st["train_channel_regroup"]["phase"], "safe")
        self.assertTrue(c.running)
        c.current_channel = 1
        st["cmd_gen"] = 9
        self.assertFalse(fn(c, st, "member", "member", 8, lambda: False))
        self.assertEqual(len(attempts), 1)

    def test_daily_city_preparation_is_independent_and_keeps_online_on_failure(self):
        ns = {"log": logging.getLogger("test"), "set_account_activity": Mock(),
              "_workflow_leave_current_area": Mock()}
        fn = function("train_bot/run_party_digioi.py", "_daily_return_to_city", ns)
        c = SimpleNamespace(running=True, current_map=23803, combat_ready=Mock())
        c.go_to_town = Mock(side_effect=lambda *args, **kw: setattr(c, "current_map", 12001))
        self.assertTrue(fn(c, "member", lambda: False))
        c.go_to_town.assert_called_once()
        c.combat_ready.assert_called_once()
        c.current_map = 23803
        c.go_to_town = Mock(return_value=False)
        self.assertFalse(fn(c, "member", lambda: False))
        self.assertTrue(c.running)

    def test_selected_pet_wins_across_all_workflows_with_default_fallback(self):
        tree = ast.parse((ROOT / "train_bot/client.py").read_text())
        node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "ensure_pet_role")
        ns = {}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "pet-role", "exec"), ns)
        c = SimpleNamespace(_ui_selected_pet_id=123, state=SimpleNamespace(battle_config={"pet_roles": {"train": 456, "quest": 789}}), switch_pet=Mock(return_value=True))
        for role in ("train", "quest", "boss"):
            self.assertTrue(ns["ensure_pet_role"](c, role))
        self.assertEqual([call.args[0] for call in c.switch_pet.call_args_list], [123, 123, 123])
        c._ui_selected_pet_id = 0
        self.assertTrue(ns["ensure_pet_role"](c, "train"))
        c.switch_pet.assert_called_with(456)

    def test_workflows_have_single_owner_and_commands_precede_legacy_recovery(self):
        source = (ROOT / "train_bot/run_party_digioi.py").read_text()
        start = source.index("        while c.running:\n")
        self.assertLess(source.index('            if st["cmd_gen"] > cmd_gen_handled:', start),
                        source.index("            # VE PET MAC DINH:", start))
        self.assertIn('all_at_source = False if kind == "train"', source)
        self.assertNotIn('START TRAIN TEAM fast-path:', source)
        self.assertTrue('st.get("ui_train_phase") != "farming"' in source)
        self.assertIn('if st.get("cmd_gen") != gen:', source)
        self.assertTrue('st["daily_participants"] = set(pending)' in (ROOT / "train_bot/workflows/daily.py").read_text())
        self.assertIn('if task != "team_dungeon":\n                        continue', source)
        self.assertIn('Daily: da xong, dung yen', source)

    def test_full_train_command_gathers_five_then_routes_only_leader(self):
        tree = ast.parse((ROOT / "train_bot/run_party_digioi.py").read_text())
        command = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_do_manual_cmd")
        names = sorted({v for n in command.body if isinstance(n, ast.Nonlocal) for v in n.names})
        assignments = ast.parse("\n".join(n + " = initial.get(" + repr(n) + ")" for n in names)).body
        factory = ast.FunctionDef(name="factory", args=ast.arguments(posonlyargs=[], args=[ast.arg(arg="initial")],
                                  kwonlyargs=[], kw_defaults=[], defaults=[]),
                                  body=assignments + [command, ast.Return(value=ast.Name(id="_do_manual_cmd", ctx=ast.Load()))],
                                  decorator_list=[])
        factory_code = compile(ast.fix_missing_locations(ast.Module(body=[factory], type_ignores=[])), "actual-command", "exec")
        users = ["leader"] + ["member" + str(i) for i in range(1, 5)]
        st = {"lock": threading.RLock(), "cmd_gen": 2, "manual_route_gen": 2,
              "reform_gen": 0, "manual_train_users": users, "manual_route_city_arrived": {},
              "manual_route_plan": None, "ui_train_phase": "gather"}
        for key in ("manual_route_plan_ready", "manual_route_party_ready", "manual_route_source_done",
                    "manual_route_done", "manual_train_channel_ready"):
            st[key] = threading.Event()
        clients = {}
        for index, user in enumerate(users):
            c = SimpleNamespace(running=True, current_map=23803, current_channel=1 if index == 0 else 2,
                                self_entity=user.encode(), party_members=[], party_leader=None,
                                pos=(550, 590), party_invite_ready=False, flee_mode=False,
                                state=SimpleNamespace(in_battle=False), stop_run_around=Mock(),
                                in_combat=lambda **kw: False, in_di_gioi=lambda: False,
                                _wait_combat_clear=Mock(), combat_ready=Mock(), leave_party=Mock(),
                                nearest_smart_city=lambda *args, **kw: {"city": 23001, "flag": 0},
                                invite_members=Mock(), set_party_strategist=Mock(),
                                pre_route_town_hop=Mock(side_effect=AssertionError("random hop forbidden")))
            def town(city, flag, client=c, **kw):
                client.current_map = city
                return True
            c.go_to_town = Mock(side_effect=town)
            def switch(channel, client=c, **kw):
                client.current_channel = channel
                return True
            c.switch_channel = Mock(side_effect=switch)
            def ready(value, client=c, member=user):
                client.party_invite_ready = value
                if value and member != "leader":
                    client.party_leader = b"leader"
                    clients["leader"].party_members.append(client.self_entity)
            c.set_party_invite_ready = Mock(side_effect=ready)
            clients[user] = c
        leader = clients["leader"]
        def route(source, destination, safe, **kw):
            self.assertEqual(source, 23001)
            self.assertEqual(destination, 23803)
            self.assertEqual(set(leader.party_members), {u.encode() for u in users[1:]})
            self.assertTrue(all(c.current_channel == 1 for c in clients.values()))
            self.assertTrue(kw["flee"])
            for c in clients.values():
                c.current_map = destination
            return True
        leader.follow_smart_scene_route = Mock(side_effect=route)
        leader.navigate_to = Mock(return_value=True)
        cfg = SimpleNamespace(TRAIN_MAPS={23803: {"safe": []}}, PARTY_LEADER_ACC={0: "leader"})
        shared = {"config": cfg, "account_clients": clients, "time": SimpleNamespace(time=time.time, monotonic=time.monotonic, sleep=lambda _: time.sleep(0.003)),
                  "log": logging.getLogger("test"), "_resolve_train_safe": lambda *args: None,
                  "set_account_activity": Mock(), "joined_member_count": lambda _: 0,  # Simulate stale local ACK count.
                  "reset_party_joined": Mock(), "_invite_whitelist_followers_if_bot_party_ready": Mock(),
                  "_resync_ck": Mock(), "READY_WAIT_REFORM_SEC": 5,
                  "_route_mismatch_timed_out": lambda *args, **kwargs: False}
        for name in ("_workflow_leave_current_area", "_open_route_member_invites", "_train_retry_leader_channel", "_train_fallback_full_channel", "_train_adopt_map_channel", "_farm_party_missing"):
            function("train_bot/run_party_digioi.py", name, shared)
        errors = []
        threads = []
        for user in users:
            ns = dict(shared, c=clients[user], st=st, username=user, label=user, pidx=0,
                      cmd_gen_handled=2, is_leader=user == "leader", is_picker=user == "leader", has_leader=True,
                      _stopped=lambda: False, _nghe_lenh_kenh=Mock(), do_channel_sync=Mock(),
                      role="LEADER" if user == "leader" else "member")
            exec(factory_code, ns)
            initial = {"mode": "digioi", "raw_mode": "digioi_train", "sc": 23001,
                       "is_digioi": True, "dt_mode": True, "digioi_solo": False,
                       "_solo_without_party": False, "training_started": False}
            fn = ns["factory"](initial)
            def run(cmd=fn):
                try:
                    cmd(("train", 0, 23803, 550, 590))
                except Exception as exc:
                    errors.append(exc)
            thread = threading.Thread(target=run, daemon=True)
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join(timeout=8)
        self.assertFalse(any(t.is_alive() for t in threads), "train deadlock")
        self.assertEqual(errors, [])
        self.assertEqual(st["ui_train_phase"], "farming")
        for c in clients.values():
            c.go_to_town.assert_called_once()
            self.assertEqual(c.go_to_town.call_args.args[0], 23001)
            c.pre_route_town_hop.assert_not_called()
        leader.follow_smart_scene_route.assert_called_once()
        leader.navigate_to.assert_called_once()
        self.assertEqual(leader.navigate_to.call_args.args, (550, 590))
        self.assertTrue(leader.navigate_to.call_args.kwargs["require_smart_path"])

    def test_route_members_open_invites_before_waiting_for_party(self):
        activity = Mock()
        client = SimpleNamespace(running=True, current_map=23001, current_channel=1,
                                 set_party_invite_ready=Mock())
        ns = {"set_account_activity": activity, "log": logging.getLogger("test")}
        fn = function("train_bot/run_party_digioi.py", "_open_route_member_invites", ns)
        self.assertTrue(fn(client, {"cmd_gen": 2}, "member", "XeTai", 2))
        client.set_party_invite_ready.assert_called_once_with(True)
        activity.assert_called_once()
        client.set_party_invite_ready.reset_mock()
        self.assertFalse(fn(client, {"cmd_gen": 3}, "member", "XeTai", 2))
        client.set_party_invite_ready.assert_not_called()
        client._individual_safe_logout = True
        self.assertFalse(fn(client, {"cmd_gen": 2}, "member", "XeTai", 2))
        client.set_party_invite_ready.assert_not_called()
        source = (ROOT / "train_bot/run_party_digioi.py").read_text()
        a = source.index("            def _do_manual_route():")
        b = source.index("            # KET BATTLE:", a)
        route = source[a:b]
        self.assertLess(route.index("_open_route_member_invites(c, st, username, label, gen)"),
                        route.index('_wait_event(st["manual_route_party_ready"]'))
        self.assertIn('st["cmd"] = tuple(cmd)', route)
        self.assertNotIn('st["cmd"] = ("route", source_req, dest)', route)
        self.assertIn('if not _wait_manual_city_arrived(expected):', route)

    def test_map_train_clears_all_dg_runtime_flags(self):
        tree = ast.parse((ROOT / "train_bot/run_party_digioi.py").read_text())
        cmd = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_do_manual_cmd")
        block = next(n for n in cmd.body if isinstance(n, ast.If))
        nonlocals = {v for n in cmd.body if isinstance(n, ast.Nonlocal) for v in n.names}
        flags = {"is_digioi", "dt_mode", "digioi_solo", "_solo_without_party"}
        self.assertTrue(flags <= nonlocals)
        ns = {"cmd": ("train", 0, 23803, 550, 590), "mode": "digioi", "raw_mode": "digioi_train",
              "config": SimpleNamespace(TRAIN_MAPS={23803: {"safe": []}}), "c": SimpleNamespace(stop_run_around=Mock()),
              "_resolve_train_safe": lambda *args: None, "label": "leader", "log": logging.getLogger("test")}
        ns.update({f: True for f in flags})
        exec(compile(ast.Module(body=block.body, type_ignores=[]), "train-runtime", "exec"), ns)
        self.assertEqual(ns["sc"], 23803)
        self.assertEqual(ns["mode"], "train")
        self.assertEqual(ns["raw_mode"], "train")
        for f in flags:
            self.assertFalse(ns[f], f)
        ns["c"].stop_run_around.assert_called_once()

    def test_map_train_config_and_no_idle_relogin(self):
        source = (ROOT / "train_bot/workflows/train.py").read_text()
        a = source.index("def party_train_map(")
        section = source[a:]
        self.assertIn('config.PARTY_CONFIG[pidx].update(mode="train", start_city_id=map_id', section)
        self.assertIn('st["dt_phase"] = "train"', section)
        self.assertIn('st["ui_dg_train_target"] = None', section)
        source = (ROOT / "train_bot/run_party_digioi.py").read_text()
        a = source.index('            if (train_on_map and is_leader and should_fight')
        condition = source[a:source.index('last_relogin = time.time()', a)]
        self.assertIn('and not st.get("ui_train_target")', condition)

    def test_team_json_is_bounded_and_omits_credentials(self):
        import io
        cfg = SimpleNamespace(PARTY_LEADER_ACC={0: "leader"}, PARTY_CONFIG={0: {"mode": "train"}}, map_display_name=lambda _: "Trác Quận")
        st = {"lock": threading.RLock(), "ui_dg_users": {"leader"}}
        client = SimpleNamespace(running=True, current_map=12001, pos=(100, 200), current_channel=2, party_members=[])
        runner = SimpleNamespace(_pstate=lambda _: st, _log_path="fake.log",
                                 party_accounts=lambda _: [("leader", "secret-password", True, 0)],
                                 account_clients={"leader": client},
                                 account_status=lambda _: {"char": "Yêu Quái"},
                                 get_account_task=lambda _: {"task": "chờ member", "phase": "wait", "elapsed": 12})
        ns = {"_get_runner": lambda: runner, "json": json, "time": time}
        fn = function("agent_bridge.py", "team_debug_json", ns)
        data = ("waiting\n" * 350 + "password=secret-password\naccess_token=secret-token\n").encode()
        with patch.dict("sys.modules", {"train_bot": SimpleNamespace(config=cfg)}), patch("builtins.open", return_value=io.BytesIO(data)):
            result = fn()
        self.assertNotIn("secret-password", result)
        self.assertNotIn("secret-token", result)
        snapshot = json.loads(result)
        self.assertEqual(len(snapshot["logs"]), 300)
        self.assertEqual(snapshot["accounts"][0]["activity"], "chờ member")
        self.assertEqual(snapshot["coordination"]["ui_dg_users"], ["leader"])

    def test_farm_requires_exact_server_roster(self):
        leader = SimpleNamespace(current_map=12001, current_channel=2, party_members=[b"other"])
        member = SimpleNamespace(running=True, current_map=12001, current_channel=2, self_entity=b"member")
        ns = {"config": SimpleNamespace(PARTY_LEADER_ACC={0: "leader"}),
              "account_clients": {"member": member}}
        fn = function("train_bot/run_party_digioi.py", "_farm_party_missing", ns)
        self.assertEqual(fn(0, ["leader", "member"], leader), ["member"])
        leader.party_members = [b"member"]
        self.assertEqual(fn(0, ["leader", "member"], leader), [])
        member.running = False
        self.assertEqual(fn(0, ["leader", "member"], leader), ["member"])

    def test_dg_handoff_waits_for_all_command_loops_and_dispatches_once(self):
        from train_bot.diagnostic_lock import WorkflowLock
        st = {"lock": WorkflowLock("test-party", max_wait=.2), "cmd_gen": 7,
              "ui_dg_train_target": (21001, 100, 200)}
        clients = {u: SimpleNamespace(running=True, in_di_gioi=lambda: False,
                                     _dg_train_ready_token=7 if u == "leader" else None,
                                     stop_run_around=Mock()) for u in ("leader", "member")}
        callbacks = []
        def dispatch_train(*args, **kwargs):
            self.assertTrue(st["lock"].acquire(blocking=False), "DG dispatch still holds party lock")
            st["lock"].release()
            st.update(cmd_gen=8)
        dispatch = Mock(side_effect=dispatch_train)
        sleeps = []
        def sleep(_seconds):
            self.assertEqual(dispatch.call_count, 0)
            sleeps.append(True)
            clients["member"]._dg_train_ready_token = 7
        fake_threads = SimpleNamespace(Thread=lambda **kw: SimpleNamespace(start=lambda: callbacks.append(kw["target"])))
        cfg = SimpleNamespace(PARTY_CONFIG={0: {}}, PARTY_LEADER_ACC={0: "leader"})
        ns = {"config": cfg, "account_clients": clients, "threading": fake_threads,
              "time": SimpleNamespace(time=lambda: 100, sleep=sleep),
              "log": logging.getLogger("test"), "_dt_party_usernames": lambda _: list(clients),
              "party_train_map": dispatch}
        fn = function("train_bot/run_party_digioi.py", "_android_dg_train_handoff", ns)
        fn(0, st)
        self.assertEqual(cfg.PARTY_CONFIG[0]["mode"], "stand")
        callbacks[0]()
        self.assertEqual(len(sleeps), 1)
        dispatch.assert_called_once_with(0, 21001, 100, 200, expected_generation=7)
        self.assertEqual(st["manual_train_users"], ["leader", "member"])
        self.assertFalse(st["ui_dg_transition_pending"])
        fn(0, st)
        self.assertEqual(len(callbacks), 1)

    def test_dg_snapshot_excludes_offline_configured_accounts(self):
        ns = {"_pstate": lambda _: {"ui_dg_users": {"leader", "member", "offline"}},
              "party_accounts": lambda _: [(u, "", False, 0) for u in ("leader", "member", "offline")],
              "is_account_running": lambda u: u != "offline",
              "account_stops": {}}
        fn = function("train_bot/run_party_digioi.py", "_dt_party_usernames", ns)
        self.assertEqual(fn(0), ["leader", "member"])

    def test_pursuit_is_movement_only_and_stops_when_workflow_blocks_it(self):
        tree = ast.parse((ROOT / "train_bot/client.py").read_text())
        node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "sync_area_combat_mode")
        ns = {"log": logging.getLogger("test")}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "client.py", "exec"), ns)
        client = SimpleNamespace(_label="test", running=True, current_map=49942,
                                 _auto_pursuit_enabled=True, _auto_battle_enabled=False,
                                 _area_combat_mode=None, _running_route=False, party_leader=None,
                                 self_entity=b"self", flee_mode=True,
                                 in_combat=lambda: False, start_run_around=Mock(),
                                 stop_run_around=Mock(), combat_ready=Mock())
        fn = ns["sync_area_combat_mode"]
        fn(client)
        self.assertEqual(client._area_combat_mode, "pursuit")
        self.assertTrue(client.flee_mode)  # pursuit khong duoc sua mode chien dau
        client.start_run_around.assert_called_once_with(stay_in_di_gioi=False)
        client.combat_ready.assert_not_called()
        client._running_route = True
        fn(client, allow_pursuit=False)
        self.assertEqual(client._area_combat_mode, "normal")
        client.stop_run_around.assert_called_once()
        client.stop_run_around.reset_mock(); client._running_route = False
        fn(client)
        self.assertEqual(client._area_combat_mode, "pursuit")
        self.assertEqual(client.start_run_around.call_count, 2)
        self.assertFalse(client._auto_battle_enabled)

    def test_dg_pursuit_requires_ground_and_generation(self):
        source = (ROOT / "train_bot/client.py").read_text()
        a = source.index('    def _run_around_loop(')
        b = source.index('    # Cap quai Di Gioi:', a)
        loop = source[a:b]
        self.assertIn('generation != self._run_around_generation', loop)
        self.assertIn('require_smart_path=True', loop)
        self.assertNotIn('self.move_to(', loop)

    def test_ui_account_controls_follow_connection_state(self):
        java = ROOT.parents[1] / "main/java/com/fen/tsbot"
        account = (java / "AccountManagerView.java").read_text()
        main = (java / "MainActivity.java").read_text()
        self.assertIn('boolean busy=online||connecting||loginPending[selected]', account)
        self.assertIn('outButton.setEnabled(online||connecting)', account)
        self.assertIn('currentUserField.setEnabled(!busy)', account)
        self.assertIn('currentPassField.setEnabled(!busy)', account)
        self.assertIn('dailyStop.setVisibility(active?View.VISIBLE:View.GONE)', main)
        self.assertIn('logoutAllButton.setVisibility(anyOnline?View.VISIBLE:View.GONE)', main)
        self.assertIn('accountManagerView.hasPendingLogin()||allConfiguredAccountsOnline()', main)
        self.assertNotIn('XEM PACKET SERVER JSON', main)

    def test_channel_policy_never_ranks_population(self):
        config = SimpleNamespace(PARTY_CONFIG={0: {}}, PARTY_LEADER_ACC={0: "leader"})
        ns = {"config": config, "_mode_can_lap_doi": lambda _: True,
              "_party_40npc_ngoai_gio": lambda *args: False,
              "time": time, "log": logging.getLogger("test")}
        fn = function("train_bot/run_party_digioi.py", "_dieu_phoi_chot_kenh", ns)
        clients = [("leader", SimpleNamespace(current_map=12001, current_channel=3)),
                   ("member", SimpleNamespace(current_map=12001, current_channel=7))]
        state = {"lock": threading.RLock(), "train_channel_manual": 7}
        self.assertEqual(fn(0, state, clients), 7)
        state = {"lock": threading.RLock()}
        self.assertEqual(fn(0, state, clients), 3)

    def test_no_empty_channel_fallback(self):
        fn = function("train_bot/run_party_digioi.py", "_kenh_trong_cho_ca_party", {})
        self.assertIsNone(fn(0, {}, [], {7}))
        ns = {"json": json}
        fn = function("agent_bridge.py", "switch_best_channel_json", ns)
        self.assertFalse(json.loads(fn())["ok"])

    def test_installer_fsync_uses_original_stream(self):
        source = (ROOT.parents[1] / "main/java/com/fen/tsbot/UpdateManager.java").read_text()
        self.assertIn('OutputStream output=session.openWrite("update.apk",0,total)', source)
        self.assertNotIn('new BufferedOutputStream', source)
        self.assertIn('session.fsync(output)', source)
        self.assertIn('done!=total', source)

    def test_installer_delegates_unreadable_v2_certificate_to_android(self):
        source = (ROOT.parents[1] / "main/java/com/fen/tsbot/UpdateManager.java").read_text()
        self.assertNotIn('APK Release chưa được ký', source)
        self.assertIn('updateSignatures.length>0&&installedSignatures.length>0', source)
        self.assertIn('PackageInstaller installer=', source)

    def test_leader_saved(self):
        save = Mock()
        ns = {"_save_account_setting": save}
        function("agent_bridge.py", "_save_leader", ns)("member2")
        self.assertEqual(ns["_selected_leader_user"], "member2")
        save.assert_called_once_with("__team__", {"leader": "member2"})

    def test_daily_recovery_does_not_disconnect(self):
        client = SimpleNamespace(_daily_use_selected_pet=True, running=True, close=Mock())
        ns = {"log": logging.getLogger("test")}
        fn = function("train_bot/run_party_digioi.py", "_force_supervisor_reconnect", ns)
        self.assertFalse(fn("member", client, "PB failed"))
        self.assertTrue(client._daily_instance_blocked)
        client.close.assert_not_called()

    def test_logout_all_members_before_leader(self):
        events = []
        clients = {u: SimpleNamespace(running=True) for u in ("leader", "member")}
        def stop(user, **kw):
            events.append(user)
            clients[user].running = False
        runner = SimpleNamespace(party_accounts=lambda _: [("leader", "", True, False), ("member", "", False, False)],
                                 account_clients=clients, stop_account=stop, is_account_running=lambda u: False)
        class Thread:
            def __init__(self, target, **kw): self.target = target
            def start(self): self.target()
        ns = {"_get_runner": lambda: runner, "json": json, "threading": SimpleNamespace(Thread=Thread),
              "time": SimpleNamespace(monotonic=lambda: 0), "log": logging.getLogger("test")}
        result = json.loads(function("agent_bridge.py", "safe_logout_all_json", ns)())
        self.assertTrue(result["ok"])
        self.assertEqual(events, ["member", "leader"])

    def test_boss_count_and_cooldown_are_server_owned(self):
        tree = ast.parse((ROOT / "train_bot/client.py").read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and any(getattr(f, "name", "") == "do_legion_boss" for f in n.body))
        method = next(n for n in cls.body if getattr(n, "name", "") == "do_legion_boss")
        source = ast.unparse(method)
        self.assertNotIn("self.relogin()", source)
        self.assertNotIn("self.legion_boss_count +=", source)
        self.assertNotIn("self.legion_boss_next =", source)

    def test_independent_daily_and_walk_combat(self):
        source = (ROOT / "train_bot/run_party_digioi.py").read_text()
        self.assertIn('if task != "team_dungeon":', source)
        self.assertIn('st.get("daily_team_generation") != cmd_gen_handled', source)
        self.assertIn('route_flee = kind == "train" or expected <= 1', source)
        self.assertIn('c.navigate_to(tx, ty, flee=True,', source)

    def test_navigation_never_counts_a_move_rejected_by_combat(self):
        source = (ROOT / "train_bot/client.py").read_text()
        start = source.index("    def navigate_to(")
        end = source.index("\n    def follow_path(", start)
        navigate = source[start:end]
        # Dinh tran giua duong -> lenh move bi NUOT -> KHONG duoc tu nhan "da toi".
        self.assertIn("_co_tran_giua_duong", navigate)
        self.assertIn("KHONG nhan la da toi", navigate)
        # CHAN MA 14: khong bao gio gui 1 lenh move xa hon MOVE_XA_TOI_DA, va _enter_gate phai
        # chia nho buoc toi cong (log 22/09 16:39:13: dist=1800 -> ma 14).
        self.assertIn("MOVE_XA_TOI_DA", source)
        self.assertIn("self._move_chia_doan(x, y)", source)
        self.assertIn("_nav_ok", source)   # execute_smart_route khong goi _enter_gate khi navigate fail

    def test_train_members_never_advance_gate_events_on_their_own(self):
        source = (ROOT / "train_bot/run_party_digioi.py").read_text()
        self.assertNotIn("gate_follow", source)
        self.assertNotIn("member vua xong battle cong -> bam tiep thoai", source)

    def test_unknown_exp_level_not_guessed(self):
        ns = {"_CHAR_EXP_LEVELS": {155: (236222752, 6290520)}}
        fn = function("agent_bridge.py", "_level_exp_values", ns)
        self.assertEqual(fn(SimpleNamespace(char_level=156, char_exp=250000000)), (None, None, None))
        self.assertEqual(fn(SimpleNamespace(char_level=155, char_exp=237360504)), (1137752, 6290520, 5152768))

    def test_raw_exp_rows_hidden_inside_battle_to_avoid_duplicate(self):
        # 1 tran chi hien bo dong chuan (battle_summary + battle_exp); dong `exp`
        # tho chi hien khi ngoai tran de UI khong lap cung gia tri.
        standalone, = methods("train_bot/client.py", "GameClient", ["_exp_row_standalone"], {"time": time})
        in_battle = SimpleNamespace(_metrics_battle_started_at=1.0, _metrics_battle_end_at=0.0)
        self.assertFalse(standalone(in_battle))
        just_ended = SimpleNamespace(_metrics_battle_started_at=None, _metrics_battle_end_at=time.time())
        self.assertFalse(standalone(just_ended))
        outside = SimpleNamespace(_metrics_battle_started_at=None, _metrics_battle_end_at=time.time() - 10)
        self.assertTrue(standalone(outside))


    def test_use_slot_wait_returns_new_count_without_waiting_full_timeout(self):
        ns = {"time": time, "_load_gamedata_items": lambda: {}}
        use_slot_wait, use_slot = methods("train_bot/client.py", "GameClient",
                                          ["use_slot_wait", "use_slot"], ns)

        class Fake:
            running = True

            def __init__(self):
                self.bag_slots = {3: [0x1111, 5]}
                self.activity_log = deque()
                self.sent = []

            def send(self, opcode, payload):
                self.sent.append((opcode, payload))
                self.bag_slots[3][1] -= 2   # gia lap server ack 0x17/0900

        Fake.use_slot = use_slot
        Fake.use_slot_wait = use_slot_wait
        client = Fake()
        started = time.time()
        ok, count = client.use_slot_wait(3, qty=2, wait=1.0)
        self.assertTrue(ok)
        self.assertEqual(count, 3)
        self.assertLess(time.time() - started, 0.5)   # thay ack la tra ngay, khong doi het timeout
        self.assertEqual(client.sent[0][0], 0x17)
        self.assertEqual(client.sent[0][1][:2], b"\x0f\x00")

    def test_use_slot_wait_refuses_empty_slot_without_sending(self):
        ns = {"time": time, "_load_gamedata_items": lambda: {}}
        use_slot_wait, use_slot = methods("train_bot/client.py", "GameClient",
                                          ["use_slot_wait", "use_slot"], ns)

        class Fake:
            running = True

            def __init__(self):
                self.bag_slots = {3: [0x1111, 0]}
                self.activity_log = deque()
                self.sent = []

            def send(self, opcode, payload):
                self.sent.append(opcode)

        Fake.use_slot = use_slot
        Fake.use_slot_wait = use_slot_wait
        client = Fake()
        self.assertEqual(client.use_slot_wait(3), (False, 0))
        self.assertEqual(client.sent, [])

    def test_solo_multipet_builds_options_for_all_pet_atypes(self):
        # DG solo: 4 pet o atype 0/1/3/4 - `_prepare_tracker_turn` PHAI gom option cho TAT CA
        # atype pet (khong loc theo my_atype cua char), khong thi pet khong ra lenh -> tran ket.
        ns = {"config": SimpleNamespace(UNIT_CHAR=3, UNIT_PET=2),
              "log": logging.getLogger("test"), "time": time}

        class U:
            def __init__(self):
                self.alive = True
                self.hp = 100

        units = {(3, 2): U(),                                   # char (my_atype=2)
                 (2, 0): U(), (2, 1): U(), (2, 3): U(), (2, 4): U(),   # 4 pet
                 (0, 0): U(), (1, 3): U()}                      # quai (enemy_rows=(0,1))

        def make(solo):
            armed = []
            client = SimpleNamespace(
                battle_tracker=SimpleNamespace(active=True, units=units, generation=5, turn=2),
                state=SimpleNamespace(enemy_rows=(0, 1), my_atype=2, solo_multipet=solo),
                available={}, last_turn_time=0.0, _acted_turn=False, auto_combat=True,
                _arm_decision=lambda: armed.append(True), _label="test")
            return client, armed

        prepare, = methods("train_bot/client.py", "GameClient", ["_prepare_tracker_turn"], ns)
        client, armed = make(True)
        prepare(client)
        pet_opts = client.available.get(2, [])
        self.assertEqual(sorted({a for a, _t in pet_opts}), [0, 1, 3, 4])   # du 4 pet
        self.assertEqual(sorted({t for _a, t in pet_opts}), [0, 3])         # cot quai
        char_opts = client.available.get(3, [])
        self.assertEqual(sorted({a for a, _t in char_opts}), [2])           # nhan vat o my_atype=2
        self.assertTrue(armed)

        # Khong solo -> chi pet o dung my_atype (khong co (2,2)) -> khong co option pet.
        client2, _ = make(False)
        prepare(client2)
        self.assertNotIn(2, client2.available)

    def test_send_not_blocked_when_coordinator_session_off(self):
        # Khi phien dieu phoi lech, KHONG duoc de `mark_sent` chan lenh danh (key cu co the
        # trung luot moi -> mat lenh -> tran tre). `mark_sent` chi chan khi phien KHOP.
        source = (ROOT / "train_bot/client.py").read_text()
        a = source.index("def _send_combat(")
        b = source.index("def flee_battle(", a)
        block = source[a:b]
        self.assertIn("elif not coordinator.mark_sent(", block)
        self.assertIn("tracker.register_action(source, d.skill", block)

    def test_tracker_battle_arms_on_0x35_offer_not_only_turn_start(self):
        # Tracker path phai arm o CA su kien `status` cua 0x35 (giong legacy `_on_actions`),
        # khong chi o `turn_start` (0x34) -> tranh "vao tran khong danh" khi 0x34 toi truoc
        # luc tracker co du don vi.
        source = (ROOT / "train_bot/client.py").read_text()
        a = source.index("def _track_battle_packet(")
        b = source.index("def _prepare_tracker_turn(", a)
        block = source[a:b]
        self.assertIn('event.kind == "status"', block)
        self.assertIn("self._prepare_tracker_turn()", block)
        self.assertIn("_acted_turn", block)
        # CHI la FALLBACK: khong arm lai khi da co option -> tranh debounce cho het burst 0x35
        # (lam lenh danh gui cham).
        self.assertIn("not self.available", block)
        # Chan doan ro khi AUTO BATTLE bat ma khong co option -> log doc duoc ly do.
        self.assertIn("KHONG co option", source)
        # Do do tre gui lenh (arm -> send) trong log SEND.
        self.assertIn("_arm_first_at", source)

    def test_combat_worker_is_pinned_to_generation_and_turn_for_solo_and_team(self):
        # Worker cua turn cu KHONG duoc gui/clear/reset state turn moi. Guard nay dung chung cho
        # DG solo multipet va party team, nen test ca hai hinh dang client de tranh sua mot luong
        # lai lam cham/mat luot luong con lai.
        ns = {"log": logging.getLogger("test"),
              "combat": SimpleNamespace(Decision=object)}
        turn_key, is_current, reset_turn, send_combat = methods(
            "train_bot/client.py", "GameClient",
            ["_combat_turn_key", "_is_current_combat_turn", "_reset_turn", "_send_combat"], ns)

        class Fake:
            _combat_turn_key = turn_key
            _is_current_combat_turn = is_current
            _reset_turn = reset_turn
            _send_combat = send_combat

        for solo_multipet, party_members in ((True, []), (False, [b"member"])):
            client = Fake()
            client.battle_tracker = SimpleNamespace(generation=12, turn=3)
            client.state = SimpleNamespace(solo_multipet=solo_multipet)
            client.party_members = party_members
            client._acted_turn = True
            client._label = "solo" if solo_multipet else "team"

            # Reset hen tu t=2 den sau khi t=3 bat dau phai la no-op.
            client._reset_turn((12, 2))
            self.assertTrue(client._acted_turn)
            # Ke ca reset cua tracker turn hien tai cung khong mo cua gui lai; chi 0x34 turn moi
            # (`_prepare_tracker_turn`) moi duoc reset `_acted_turn`.
            client._reset_turn((12, 3))
            self.assertTrue(client._acted_turn)
            # SEND cua worker cu bi chan truoc khi cham coordinator/socket.
            decision = SimpleNamespace(unit=3, atype=2, b=3, target=0, skill=10000)
            self.assertFalse(client._send_combat(decision, expected_key=(12, 2)))

        source = (ROOT / "train_bot/client.py").read_text()
        self.assertIn("available_snapshot", source)
        self.assertIn("bo worker combat CU", source)

    def test_machinebox_pause_rearms_train_without_immediately_banning_map(self):
        handler, resume = methods(
            "train_bot/client.py", "GameClient",
            ["_handle_machinebox_paused", "_resume_machinebox_after_battle"],
            {"log": logging.getLogger("test"), "time": time})

        class Fake:
            _handle_machinebox_paused = handler
            _resume_machinebox_after_battle = resume

            def __init__(self):
                self._label = "leader"
                self.current_map = 23803
                self._auto_battle_enabled = True
                self._machinebox_force_paused = False
                self._machinebox_pause_sent_at = 0.0
                self._machinebox_rearm_at = 0.0
                self._machinebox_rearm_map = None
                self._machinebox_rearm_pending_map = None
                self._machinebox_map_cam = set()
                self.state = SimpleNamespace(in_battle=False)
                self.sent = []

            def in_pb_quest_event(self):
                return False

            def machinebox_payload(self):
                return b"flags"

            def send(self, opcode, payload):
                self.sent.append((opcode, payload))

        client = Fake()
        self.assertTrue(client._handle_machinebox_paused())
        self.assertEqual(client.sent, [(0x41, b"\x01\x00flags")])
        self.assertNotIn(23803, client._machinebox_map_cam)
        self.assertFalse(client._machinebox_server_paused)

        # Chi pause quay lai NGAY sau chinh re-arm moi la bang chung server tu choi map.
        self.assertFalse(client._handle_machinebox_paused())
        self.assertIn(23803, client._machinebox_map_cam)
        self.assertEqual(len(client.sent), 1)

        forced = Fake()
        forced._machinebox_force_paused = True
        self.assertFalse(forced._handle_machinebox_paused())
        self.assertEqual(forced.sent, [])

        # Pause den trong tran chi ghi pending, tuyet doi khong chen 0x41 vao combat.
        during = Fake()
        during.state.in_battle = True
        self.assertFalse(during._handle_machinebox_paused())
        self.assertEqual(during.sent, [])
        self.assertEqual(during._machinebox_rearm_pending_map, 23803)
        during.state.in_battle = False
        self.assertTrue(during._resume_machinebox_after_battle())
        self.assertEqual(during.sent, [(0x41, b"\x01\x00flags")])
        self.assertIsNone(during._machinebox_rearm_pending_map)

    def test_navigate_compensation_does_not_call_removed_route_guard(self):
        source = (ROOT / "train_bot/client.py").read_text()
        start = source.index("    def navigate_to(")
        end = source.index("    def follow_path(", start)
        block = source[start:end]
        self.assertNotIn("_nav_con_hieu_luc", block)
        # Vong di bu van co du ba dieu kien dung hop le.
        self.assertIn("while _them < 8 and self.running", block)
        self.assertIn("if abort and abort():", block)
        self.assertIn("if _da_doi_map():", block)

    def test_auto_mode_slot_five_uses_saved_ui_slot_not_compacted_party_index(self):
        runner = SimpleNamespace(party_accounts=lambda _:
            [("acc1", "", True, True), ("acc2", "", False, False),
             ("acc3", "", False, False), ("acc5", "", False, False)])
        apply_mode = Mock(return_value='{"ok": true}')
        ns = {"json": json, "_get_runner": lambda: runner,
              "_account_slots": {"acc1": 0, "acc2": 1, "acc3": 2, "acc5": 4},
              "set_auto_mode_json": apply_mode}
        fn = function("agent_bridge.py", "set_auto_mode_slot_json", ns)
        result = json.loads(fn(4, "acc5", "battle"))
        self.assertTrue(result["ok"])
        apply_mode.assert_called_once_with("acc5", "battle")

        stale = json.loads(fn(3, "acc5", "battle"))
        self.assertFalse(stale["ok"])
        self.assertIn("Dữ liệu tab đã thay đổi", stale["message"])

    def test_android_auto_cache_is_owned_by_slot_and_username(self):
        java = ROOT.parents[1] / "main/java/com/fen/tsbot"
        account = (java / "AccountManagerView.java").read_text()
        main = (java / "MainActivity.java").read_text()
        self.assertIn("localAutoBattleUser", account)
        self.assertIn("u.equals(localAutoBattleUser[i])", account)
        self.assertIn("user.equals(a.optString(\"user\"))", account)
        self.assertIn("toggleAutoOptimistic(slot,u,mode)", main)
        self.assertIn("setAutoState(slot,u,", main)

    def test_digioi_mode_option_exposed_in_apk_and_bridge(self):
        java = ROOT.parents[1] / "main/java/com/fen/tsbot"
        main = (java / "MainActivity.java").read_text()
        bridge = (ROOT / "agent_bridge.py").read_text()
        runtime = (ROOT / "train_bot/run_party_digioi.py").read_text()
        # UI co spinner party/solo + gia tri gui len bridge.
        self.assertIn("digioiModeSpinner", main)
        self.assertIn('?"solo":"party";', main)
        self.assertIn('put("digioi_mode",digioiModeValue())', main)
        self.assertIn('callAttr("start_farm_mode_json",mode,mid,x,y,diGioiLevel,digioiModeValue())', main)
        # Bridge nhan + forward vao config (setup_party_runtime nam o run_party_digioi.py).
        self.assertIn('def start_farm_mode_json(mode, map_id, x, y, di_gioi_level=2, digioi_mode="party")', bridge)
        self.assertIn('digioi_mode=("solo" if str(data.get("digioi_mode"', bridge)
        self.assertIn('"digioi_mode": digioi_mode', runtime)

    def test_map_renders_static_layer_once_and_interpolates_dynamic_positions(self):
        java = ROOT.parents[1] / "main/java/com/fen/tsbot"
        team = (java / "TeamMapView.java").read_text()
        account = (java / "AccountManagerView.java").read_text()
        # Lop TINH (nen/luoi/dia hinh/safe/dich) ve 1 lan vao bitmap, chi ve lai khi doi vung nhin.
        self.assertIn("staticBmp", team)
        self.assertIn("drawStatic", team)
        self.assertIn("staticKey", team)
        # Lop DONG noi suy vi tri giua 2 snapshot -> muot, va chi ve lai khi co thay doi.
        self.assertIn("updateAnimTargets", team)
        self.assertIn("postOnAnimation", team)
        self.assertIn("ANIM_MS", team)
        # Man BAN DO full-screen: an title + ScrollView, hien mapHost.
        self.assertIn("mapHost.setVisibility(VISIBLE)", account)
        self.assertIn("bodyScroll.setVisibility(GONE)", account)

    def test_bag_ui_updates_in_place_and_preserves_scroll(self):
        java = ROOT.parents[1] / "main/java/com/fen/tsbot"
        account = (java / "AccountManagerView.java").read_text()
        main = (java / "MainActivity.java").read_text()
        # Giu vi tri cuon khi dung lai cay View (dashboard poll / thao tac).
        self.assertIn("bodyScroll=new ScrollView(c)", account)
        self.assertIn("renderBodyInner();", account)
        self.assertIn("bodyScroll.scrollTo(0,keepY)", account)
        # Tab RƯƠNG ĐỒ cap nhat SO LUONG TAI CHO, khong dung lai -> khong reset cuon.
        self.assertIn('updateBagLive(bagAcc.optString("user")', account)
        self.assertIn("markBagActionPending", account)
        self.assertIn("progressBarStyleSmall", account)   # icon spinner bao dang xu ly nen
        self.assertIn("finishBagAction", account)
        # Lenh tui do chay tren executor RIENG (khong xep sau dashboard poll) + doc lai 1 tui.
        self.assertIn("actionIo", main)
        self.assertIn('callAttr("bag_json",user)', main)


if __name__ == "__main__":
    unittest.main()
