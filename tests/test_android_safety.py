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
        safe.assert_called_once_with(0, 2, keep_auto=False)
        c.switch_channel.assert_not_called()
        safe.reset_mock()
        st["cmd"] = ("channel", 2)
        self.assertEqual(fn(0, st, [("leader", c)], 2), 0)
        safe.assert_not_called()
        # AUTO phan khu vang: giu co auto khi doi khu (khong tat auto).
        safe.reset_mock()
        st["cmd"] = ("train",)
        st["train_channel_auto"] = True
        self.assertEqual(fn(0, st, [("leader", c)], 2), 0)
        safe.assert_called_once_with(0, 2, keep_auto=True)

    def test_auto_channel_decision_is_reachable_when_party_together(self):
        # Bug cu: nhanh auto nam SAU `if len(dem) <= 1: return` VA bi nhanh manual `return` chan
        # -> tich auto ma khong bao gio doi khu. Nay auto phai chay TRUOC ca hai.
        src = (ROOT / "train_bot/run_party_digioi.py").read_text()
        a = src.index("def _dieu_phoi_chot_kenh(")
        nxt = src.find("\ndef ", a + 1)
        block = src[a:] if nxt == -1 else src[a:nxt]
        self.assertIn("if _manual > 0 and not _auto:", block)
        self.assertIn("_chot_kenh_auto_vang(pidx, st, song, dem, map_chung, leader)", block)
        self.assertLess(block.index("_chot_kenh_auto_vang(pidx"),
                        block.index("if len(dem) <= 1:"))

    def test_auto_golden_channel_only_at_farm_with_two_teams(self):
        # Checkbox 'tu chon phan khu vang': chi doi khu khi DA o bai train (farming), ca team CUNG
        # 1 kenh, leader thay >= 2 doi quanh bai; chon kenh it NGUOI KHAC nhat con du cho ca team.
        # LUU Y: `dang_o` trong bang DA tinh ca acc cua chinh team -> kenh hien tai toi thieu bang
        # `len(team)`; xep hang theo `dang_o - phan_cua_minh` (so nguoi khac).
        leader2 = SimpleNamespace(nearby_other_team_count=lambda: 2)
        leader1 = SimpleNamespace(nearby_other_team_count=lambda: 1)
        # Team (5) dang o kenh 1 (bang ghi 7 nguoi -> 2 nguoi khac); kenh 2 co 1 nguoi (vang hon).
        bang = {"bang": {1: (7, 9), 2: (1, 9), 5: (2, 9)}}
        ns = {"log": logging.getLogger("test"),
              "_map_train_dich": lambda pidx, st: 23803,
              "_lam_moi_ds_kenh": lambda *a: None,
              "_bang_kenh": lambda song, map_id=None: bang["bang"]}
        fn = function("train_bot/run_party_digioi.py", "_chot_kenh_auto_vang", ns)
        base = {"lock": threading.RLock(), "train_channel_auto": True,
                "ui_train_phase": "farming", "ui_train_target": (23803, 550, 590)}
        team = [("l", leader2)] * 5
        # Auto TAT -> khong lam gi.
        self.assertIsNone(fn(0, dict(base, train_channel_auto=False), team, {1: 5}, 23803, leader2))
        # Chua toi bai train -> khong doi khu.
        self.assertIsNone(fn(0, dict(base, ui_train_phase="gather"), team, {1: 5}, 23803, leader2))
        # Quanh bai < 2 doi -> giu nguyen khu.
        self.assertIsNone(fn(0, base, team, {1: 5}, 23803, leader1))
        # >=2 doi, party cung kenh -> chon kenh it NGUOI KHAC nhat du cho (kenh 2: 1 nguoi khac).
        st = dict(base)
        self.assertEqual(fn(0, st, team, {1: 5}, 23803, leader2), 2)
        self.assertEqual(st["auto_channel_pick"], 2)
        # Kenh minh dang o da la vang nhat -> GIU NGUYEN, khong nhay (chong ping-pong).
        bang["bang"] = {1: (7, 9), 2: (9, 9), 5: (2, 9)}
        self.assertIsNone(fn(0, dict(base), team, {1: 5}, 23803, leader2))
        # Da o dung kenh vang do -> khong doi.
        bang["bang"] = {2: (6, 9), 5: (2, 9)}
        self.assertIsNone(fn(0, dict(base), team, {2: 5}, 23803, leader2))

    def test_auto_picker_keeps_current_channel_when_capacity_unknown(self):
        # LOI THAT (log 01/10): server KHONG liet ke kenh minh dang o -> client luu `(None, None)` ->
        # `_bang_kenh` bo no ra khoi bang -> picker tuong kenh hien tai "khong du cho" -> doi sang
        # kenh khac; doi xong kenh cu lai thanh "vang nhat" -> NHAY KENH 4<->9 VO TAN. Phai GIU
        # NGUYEN khi kenh hien tai khong co so (chua ro suc chua).
        leader2 = SimpleNamespace(nearby_other_team_count=lambda: 3)
        bang = {"bang": {4: (2, 6), 7: (3, 5)}}      # thieu kenh 9 (minh dang o)
        ns = {"log": logging.getLogger("test"),
              "_map_train_dich": lambda pidx, st: 23803,
              "_lam_moi_ds_kenh": lambda *a: None,
              "_bang_kenh": lambda song, map_id=None: bang["bang"]}
        fn = function("train_bot/run_party_digioi.py", "_chot_kenh_auto_vang", ns)
        st = {"lock": threading.RLock(), "train_channel_auto": True,
              "ui_train_phase": "farming", "ui_train_target": (23803, 550, 590),
              "auto_channel_pick": 9, "auto_channel_map": 23803}
        team = [("l", leader2)] * 5
        self.assertIsNone(fn(0, st, team, {9: 5}, 23803, leader2))
        self.assertEqual(st["auto_channel_pick"], 9)

    def test_channel_cmd_unlocked_after_all_accounts_done(self):
        # `cmd=("channel", ch)` phai duoc tra ve lenh train (hoac xoa) khi CA party xu ly xong; neu
        # khong no khoa vinh vien moi lenh kenh sau + tat recovery train -> doi kenh xong khong ra
        # lai bai farm (loi user bao 30/09).
        rp = (ROOT / "train_bot/run_party_digioi.py").read_text()
        self.assertIn("def _mark_channel_cmd_done(", rp)
        self.assertIn("_mark_channel_cmd_done(pidx, st, username)", rp)

    def test_gui_train_leader_goes_back_to_spot_after_regroup(self):
        # GUI START TRAIN: nhanh legacy (`VIEC_RA_QUAI`) bi TAT khi co `ui_train_target`
        # (`_legacy_party_train_enabled` -> False), nen phai co nhanh RIENG keo ca doi ra lai diem
        # quai sau khi doi phan khu / lap lai PT. Thieu no: ca doi dung im o safe ma van "farming"
        # (loi user 30/09-01/10).
        rp = (ROOT / "train_bot/run_party_digioi.py").read_text()
        self.assertIn("GUI-TRAIN: du doi + cung map/kenh nhung con o", rp)
        self.assertIn("KEO CA DOI RA BAI", rp)

    def test_external_invite_policy_gates_input_and_bumps_generation(self):
        # Checkbox + textfield user ngoai: bat ma khong co ten -> loi (khong bat); doi thiet lap ->
        # tang `gen` de phien moi; tat -> khong lam gi.
        st = {"lock": threading.RLock()}
        runner = SimpleNamespace(_pstate=lambda _i: st)
        ns = {"json": json, "log": logging.getLogger("test"), "_get_runner": lambda: runner}
        fn = function("agent_bridge.py", "set_external_invite_json", ns)
        self.assertFalse(json.loads(fn(True, ""))["ok"])
        self.assertFalse(st.get("ext_invite_on", False))
        r = json.loads(fn(True, "  nguoichoi  "))
        self.assertTrue(r["ok"])
        self.assertTrue(st["ext_invite_on"])
        self.assertEqual(st["ext_invite_name"], "nguoichoi")
        gen1 = st["ext_invite_gen"]
        fn(True, "khac")
        self.assertGreater(st["ext_invite_gen"], gen1)
        fn(False, "")
        self.assertFalse(st["ext_invite_on"])
        self.assertEqual(st["ext_invite_status"], "idle")

    def test_external_invite_waits_then_gives_up(self):
        # Leader moi user ngoai toi da 5 phut: da vao -> xong; party du 5 -> bo qua; het 5 phut ->
        # huy lenh; tat -> khong lam gi.
        now = time.time()
        ent = b"ABCDEFGH"

        class C:
            running = True
            party_members = []
            entity_names = {ent: {"nguoichoi"}}

            def _entity_is_visible_on_current_scene(self, e):
                return True, ""

            def invite_entity(self, e):
                self.invited = True

        def base_st(**kw):
            d = {"lock": threading.RLock(), "cmd_gen": 1, "reform_gen": 0,
                 "ext_invite_on": True, "ext_invite_name": "nguoichoi",
                 "ext_invite_gen": 1, "ext_invite_gen_done": -1,
                 "ext_invite_started_at": now, "ext_invite_last_at": now,
                 "ext_invite_status": "idle"}
            d.update(kw)
            return d

        ns = {"time": SimpleNamespace(time=time.time, sleep=lambda _s: None),
              "log": logging.getLogger("test"),
              "EXT_INVITE_TIMEOUT_SEC": 300.0, "EXT_INVITE_GAP_SEC": 5.0, "PARTY_MAX_MEMBERS": 5,
              "_tim_entity_theo_ten": lambda c, n: ent,
              "_ext_invite_finish": lambda st, g, label, name, status, msg: st.update(
                  {"ext_invite_status": status, "ext_invite_gen_done": g})}
        fn = function("train_bot/run_party_digioi.py", "_cho_user_ngoai_vao_party", ns)
        # Da vao party -> xong ngay.
        st = base_st()
        c = C(); c.party_members = [ent]
        self.assertTrue(fn(c, st, 0, "L", gen=1, stopped=lambda: False))
        self.assertEqual(st["ext_invite_status"], "joined")
        # Party da du 5 nguoi -> khong con cho.
        st2 = base_st()
        c2 = C(); c2.party_members = [b"1", b"2", b"3", b"4"]
        self.assertTrue(fn(c2, st2, 0, "L", gen=1, stopped=lambda: False))
        self.assertEqual(st2["ext_invite_status"], "full")
        # Het 5 phut chua vao -> huy lenh, chay tiep flow.
        st3 = base_st(ext_invite_started_at=now - 301.0)
        self.assertTrue(fn(C(), st3, 0, "L", gen=1, stopped=lambda: False))
        self.assertEqual(st3["ext_invite_status"], "timeout")

        # Thay entity nhung KHONG co co `nearby` -> VAN moi (ten chi dinh ro), roi bi ngat.
        class C2(C):
            def _entity_is_visible_on_current_scene(self, e):
                return False, "chua thay quanh leader"

        c4 = C2(); c4.invited = False
        seen = {"n": 0}

        def stopped():
            seen["n"] += 1
            return seen["n"] > 1

        self.assertFalse(fn(c4, base_st(ext_invite_last_at=now - 10.0), 0, "L", gen=1,
                             stopped=stopped))
        self.assertTrue(c4.invited)

        # Tat -> khong lam gi.
        self.assertTrue(fn(C(), base_st(ext_invite_on=False), 0, "L", gen=1,
                             stopped=lambda: False))

    def test_external_invite_hooked_into_leader_party_gather(self):
        src = (ROOT / "train_bot/run_party_digioi.py").read_text()
        self.assertIn("def _cho_user_ngoai_vao_party(", src)
        self.assertIn("_cho_user_ngoai_vao_party(", src)
        self.assertIn("gen=gen, stopped=_stopped", src)
        self.assertIn("def set_external_invite_json(", (ROOT / "agent_bridge.py").read_text())
        java = (Path(__file__).resolve().parents[1]
                / "app/src/main/java/com/fen/tsbot/MainActivity.java").read_text()
        self.assertIn("set_external_invite_json", java)
        self.assertIn("extInviteName", java)
        # Da BO checkbox theo yeu cau user: ap dung/tat bang NUT, khong con checkbox.
        self.assertNotIn("extInviteCheck", java)

    def test_ext_invite_session_reset_reinvites_each_login(self):
        # Sau logout ALL + login lai, leader phai MOI LAI user ngoai (khong bo qua vi gen_done cu).
        st = {"lock": threading.RLock(), "ext_invite_on": True, "ext_invite_name": "nguoichoi",
              "ext_invite_gen": 3, "ext_invite_gen_done": 3,
              "ext_invite_started_at": 123.0, "ext_invite_last_at": 456.0,
              "ext_invite_status": "timeout"}
        ns = {}
        fn = function("train_bot/run_party_digioi.py", "_ext_invite_session_reset", ns)
        fn(st)
        self.assertEqual(st["ext_invite_gen_done"], -1)
        self.assertEqual(st["ext_invite_started_at"], 0.0)
        self.assertEqual(st["ext_invite_last_at"], 0.0)
        self.assertEqual(st["ext_invite_status"], "waiting")
        # Tat -> khong dung gi.
        off = {"lock": threading.RLock(), "ext_invite_on": False, "ext_invite_name": "",
               "ext_invite_gen_done": 9}
        fn(off)
        self.assertEqual(off["ext_invite_gen_done"], 9)

    def test_ext_invite_counts_external_user_in_expected(self):
        ab = (ROOT / "agent_bridge.py").read_text()
        self.assertIn("expected_total = len(configured) + (1 if ext_invite_on else 0)", ab)
        self.assertIn('"party_expected": int(expected_total)', ab)

    def test_channel_change_refarms_party_and_returns_to_farm_spot(self):
        # Sau khi doi phan khu (AUTO vang / manual): phai LAP LAI party (gom ca user ngoai neu bat)
        # roi KEO CA DOI RA LAI BAI. Truoc day: thieu user ngoai + dung im o safe.
        rp = (ROOT / "train_bot/run_party_digioi.py").read_text()
        a = rp.index("def _party_tai_cho_xu_ly(")
        b = rp.index("def _start_training(", a)
        block = rp[a:b]
        self.assertIn("nonlocal training_started", block)
        self.assertIn("_cho_user_ngoai_vao_party(c, st, pidx, label", block)
        self.assertIn("training_started = False", block)
        c0 = rp.index('if kind == "channel":')
        c1 = rp.index('elif kind == "city":', c0)
        self.assertIn("training_started = False", rp[c0:c1])

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
                  "_cho_user_ngoai_vao_party": Mock(return_value=True),
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
        # Hook moi user ngoai phai duoc goi trong luong train cua leader (truoc khi keo ra bai).
        self.assertTrue(shared["_cho_user_ngoai_vao_party"].called)
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
              "_event_channel_policy_active": lambda *args: False,
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

    def test_support_actions_are_event_only_and_farm_stays_attack_only(self):
        # Yeu cau user: hoi sinh/CC/buff bao ve/heal/hoi SP CHI chay o luong EVENT (40NPC/2K).
        # Luong FARM (train/city/digioi) dat support_combat=False -> combat chi danh thuan:
        # khong barrier dong bo -> ra lenh nhanh toi da.
        st = (ROOT / "train_bot/state.py").read_text()
        self.assertIn("self.support_combat = False", st)
        rp = (ROOT / "train_bot/run_party_digioi.py").read_text()
        self.assertIn('c.state.support_combat = (mode == "event")', rp)
        cb = (ROOT / "train_bot/combat.py").read_text()
        # Cac block ho tro khong con bi comment: da bat lai CO GATE (truoc day comment het ->
        # mat han hoi sinh/heal ca o event).
        self.assertNotIn("# rv = _try_revive(state, config.UNIT_CHAR", cb)
        self.assertNotIn("# rv = _try_revive(state, config.UNIT_PET", cb)
        # Ca 3 diem quyet dinh deu phai gate bang flag truoc khi lam bat ky buoc ho tro nao.
        for name in ("def _custom_decision(", "def decide_char(", "def decide_pet("):
            a = cb.index(name)
            nxt = cb.find("\ndef ", a + 1)
            block = cb[a:] if nxt == -1 else cb[a:nxt]
            self.assertIn('if getattr(state, "support_combat", False):', block)

    def test_register_current_unit_is_noop_when_support_off(self):
        # FARM (support_combat=False): khong dang ky _support_reg/_revive_reg -> khong ton cong
        # moi luot + khong bom rac vao 2 dict module-global khong bao gio duoc don.
        calls = []
        ns = {"_hang_cua": lambda _s, _u: 3,
              "register_support_skills": lambda *a: calls.append(a)}
        fn = function("train_bot/combat.py", "_register_current_unit", ns)
        fn(SimpleNamespace(self_slot=0, party_idx=0, support_combat=False), 3, [1])
        self.assertEqual(calls, [])
        fn(SimpleNamespace(self_slot=0, party_idx=0, support_combat=True), 3, [1])
        self.assertEqual(len(calls), 1)

    def test_event_channel_policy_roundtrip(self):
        st = {"lock": threading.RLock()}
        runner = SimpleNamespace(
            _pstate=lambda _i: st,
            party_accounts=lambda _i: [("leader", "p", True, None), ("m1", "p", False, None)])
        c = SimpleNamespace(current_map=10991, current_channel=1, running=True, _username="leader")
        rows = [{"id": 7, "current": 2, "capacity": 6, "free": 4}]
        ns = {"json": json, "log": logging.getLogger("test"), "time": time,
              "_get_runner": lambda: runner,
              "_live_party": lambda r: [("leader", c)],
              "_channel_rows_for_map": lambda cl, force=False, wait=False: list(rows)}
        fn = function("agent_bridge.py", "set_event_channel_policy_json", ns)
        r = json.loads(fn(True, 0))
        self.assertTrue(r["ok"])
        self.assertTrue(st["event_channel_auto"])
        r = json.loads(fn(False, 7))
        self.assertTrue(r["ok"])
        self.assertFalse(st["event_channel_auto"])
        self.assertEqual(st["event_channel_manual"], 7)
        rows[0]["free"] = 1   # can 2 thanh vien, con 1 -> khong du
        r = json.loads(fn(False, 7))
        self.assertFalse(r["ok"])
        self.assertIn("không đủ", r["message"])
        r = json.loads(fn(False, 99))   # khu khong ton tai
        self.assertFalse(r["ok"])
        self.assertIn("không có", r["message"])

    def _event_picker_ns(self, bang, sentinel):
        return {
            "_K40_NA": sentinel, "time": time, "log": logging.getLogger("test"),
            "config": SimpleNamespace(PARTY_CONFIG={0: {"mode": "event", "event_key": "npc_40"}}),
            "_event_channel_policy_active": lambda pidx, st: True,
            "_ev_cua_party": lambda pcfg: {"dest_map": 10991},
            "_lam_moi_ds_kenh": lambda *a: None,
            "_bang_kenh": lambda song, mid=None: dict(bang),
            "_doc_ket_qua_doi_kenh": lambda song: (set(), False, False),
            "_bao_khong_du_cho_40npc": Mock(),
        }

    def test_event_channel_picker_auto_picks_emptiest(self):
        sentinel = object()
        st = {"lock": threading.RLock(), "event_channel_auto": True, "event_channel_manual": 0,
              "event_channel_pick": 0, "event_channel_map": 0, "event_channel_status": ""}
        c = SimpleNamespace(current_map=10991, current_channel=1,
                            switch_channel=Mock(return_value=True))
        bang = {1: (10, 5), 2: (2, 10), 3: (0, 1)}   # can 5: khu 3 khong du -> chon khu 2 (it nguoi)
        ns = self._event_picker_ns(bang, sentinel)
        fn = function("train_bot/run_party_digioi.py", "_chot_kenh_40npc", ns)
        pick = fn(0, st, [("leader", c)], 5, "leader", c)
        self.assertEqual(pick, 2)
        c.switch_channel.assert_called_once_with(2, theo_lenh=True)
        ns["_bao_khong_du_cho_40npc"].assert_not_called()

    def test_event_channel_picker_counts_external_user(self):
        # Yeu cau: khu chon phai du cho CA bot LAN user ngoai (khi bat AP DUNG MOI NGOAI).
        sentinel = object()
        st = {"lock": threading.RLock(), "event_channel_auto": True, "event_channel_manual": 0,
              "event_channel_pick": 0, "event_channel_map": 0, "event_channel_status": "",
              "ext_invite_on": True, "ext_invite_name": "nguoichoi"}
        c = SimpleNamespace(current_map=10991, current_channel=1,
                            switch_channel=Mock(return_value=True))
        # 2 bot + 1 nguoi ngoai = can 3: khu 1 (con 2) KHONG du, khu 2 (con 3) DU -> chon khu 2.
        bang = {1: (0, 2), 2: (0, 3)}
        ns = self._event_picker_ns(bang, sentinel)
        fn = function("train_bot/run_party_digioi.py", "_chot_kenh_40npc", ns)
        pick = fn(0, st, [("leader", c)], 2, "leader", c)
        self.assertEqual(pick, 2)

    def test_gather_invites_external_user_both_farm_and_event(self):
        # Sau khi du bot (FARM lan 40NPC), leader phai MOI USER NGOAI (neu bat) truoc khi ra bai/
        # vao su kien. Truoc day chi gate `if event_party_mode` -> che do FARM doi phan khu xong
        # chi pt cac bot, THIEU nguoi ngoai (loi user bao 30/09).
        rp = (ROOT / "train_bot/run_party_digioi.py").read_text()
        a = rp.index("DU PARTY (%d/%d member join)")
        b = rp.index("def _start_training(", a)
        block = rp[a:b]
        self.assertNotIn("if event_party_mode:", block)   # khong con gate theo mode
        self.assertIn("_cho_user_ngoai_vao_party(c, st, pidx, label", block)

    def test_channel_switch_reopens_external_invite_session(self):
        # Doi phan khu = huy PT roi lap lai -> nguoi NGOAI bi bo ra khoi doi. Phai mo lai PHIEN moi
        # de `_cho_user_ngoai_vao_party` MOI LAI (khong thi `ext_invite_gen_done == gen` -> bo qua
        # im lang, leader chi pt cac bot - dung loi user bao 30/09).
        rp = (ROOT / "train_bot/run_party_digioi.py").read_text()
        a = rp.index("def party_switch_channel(")
        b = rp.index("def party_move_to(", a)
        self.assertIn("_ext_invite_session_reset(st)", rp[a:b])

    def test_party_reform_reopens_external_invite_session(self):
        # Cac cho huy PT de lap lai (tai cho / reform / lenh doi kenh tay) cung phai mo lai phien moi.
        rp = (ROOT / "train_bot/run_party_digioi.py").read_text()
        self.assertGreaterEqual(rp.count("_ext_invite_session_reset(st)"), 4)

    def test_event_channel_picker_default_converges_to_leader_channel(self):
        # KHONG bat AUTO, KHONG ghim MANUAL -> phai HOI TU ve kenh hien tai cua leader (keo member
        # dang o kenh khac ve), khong duoc tra `_K40_NA`/0 lam member dung nguyen kenh (bug 30/09).
        sentinel = object()
        st = {"lock": threading.RLock(), "event_channel_auto": False, "event_channel_manual": 0,
              "event_channel_pick": 0, "event_channel_map": 0, "event_channel_status": ""}
        c = SimpleNamespace(current_map=10991, current_channel=2, switch_channel=Mock(return_value=True))
        m = SimpleNamespace(current_map=10991, current_channel=3, switch_channel=Mock(return_value=True))
        ns = self._event_picker_ns({2: (1, 10), 3: (4, 10)}, sentinel)
        fn = function("train_bot/run_party_digioi.py", "_chot_kenh_40npc", ns)
        self.assertEqual(fn(0, st, [("leader", c), ("m", m)], 2, "leader", c), 2)

    def test_event_channel_picker_converged_returns_zero(self):
        sentinel = object()
        st = {"lock": threading.RLock(), "event_channel_auto": False, "event_channel_manual": 0,
              "event_channel_pick": 0, "event_channel_map": 0, "event_channel_status": ""}
        c = SimpleNamespace(current_map=10991, current_channel=2, switch_channel=Mock(return_value=True))
        m = SimpleNamespace(current_map=10991, current_channel=2, switch_channel=Mock(return_value=True))
        ns = self._event_picker_ns({2: (2, 10)}, sentinel)
        fn = function("train_bot/run_party_digioi.py", "_chot_kenh_40npc", ns)
        self.assertEqual(fn(0, st, [("leader", c), ("m", m)], 2, "leader", c), 0)
        c.switch_channel.assert_not_called()

    def test_event_leader_reruns_channel_sync_on_resync(self):
        # Leader cung phai chay lai picker khi co RE-SYNC (truoc day chi member -> leader khong chon
        # lai kenh -> member cho channel_ready mai -> ket 1 nguoi 1 kenh).
        rp = (ROOT / "train_bot/run_party_digioi.py").read_text()
        self.assertIn("(LEADER) co RE-SYNC -> chay lai dong bo kenh", rp)

    def test_send_blocks_event_step_during_battle(self):
        # Ma 47 <ket thuc su kien khi tran chua ket thuc>: `0x14 06` gui khi dang trong tran -> server
        # ngat. Phai chan o cua `send()` (luoi cuoi cung moi duong).
        src = (ROOT / "train_bot/client.py").read_text()
        self.assertIn("CHAN 0x14 06 (buoc su kien) vi DANG TRONG TRAN", src)

    def test_leader_kick_does_not_logout_whole_party(self):
        # Leader bi KICK (ma 5/47/90) -> member PHAI o lai, khong duoc set leader_gone (set = ca
        # party out theo, bug user 30/09).
        rp = (ROOT / "train_bot/run_party_digioi.py").read_text()
        self.assertIn("KHONG set leader_gone, member o lai cho", rp)
        self.assertIn('st["leader_manual_off"] = False', rp)

    def test_event_channel_picker_uses_defined_song(self):
        # Regression (log 30/09): `_chot_kenh_40npc` goi trong `do_channel_sync` -- o do KHONG co
        # bien `song` -> truyen `song` gay NameError -> run_account crash -> leader RELOGIN -> ma 90
        # -> OUT truoc khi gom PT. Phai truyen `_acc_song(pidx)`.
        rp = (ROOT / "train_bot/run_party_digioi.py").read_text()
        self.assertIn("else _chot_kenh_40npc(pidx, st, _acc_song(pidx), need, label, c)", rp)
        self.assertNotIn("else _chot_kenh_40npc(pidx, st, song, need, label, c)", rp)

    def test_event_channel_picker_manual_rejects_when_not_enough(self):
        sentinel = object()
        st = {"lock": threading.RLock(), "event_channel_auto": False, "event_channel_manual": 7,
              "event_channel_pick": 0, "event_channel_map": 0, "event_channel_status": ""}
        c = SimpleNamespace(current_map=10991, current_channel=1,
                            switch_channel=Mock(return_value=True))
        ns = self._event_picker_ns({7: (9, 1)}, sentinel)   # khu 7 chi con 1 cho, can 5
        fn = function("train_bot/run_party_digioi.py", "_chot_kenh_40npc", ns)
        pick = fn(0, st, [("leader", c)], 5, "leader", c)
        self.assertIsNone(pick)
        ns["_bao_khong_du_cho_40npc"].assert_called_once()
        c.switch_channel.assert_not_called()

    def test_ui_notice_queue(self):
        from train_bot import ui_notice
        ui_notice.clear()
        ui_notice.push("a")
        seq = ui_notice.push("b")
        data = ui_notice.poll(0)
        self.assertEqual([n["message"] for n in data["notices"]], ["a", "b"])
        self.assertEqual(data["seq"], seq)
        self.assertEqual(ui_notice.poll(seq)["notices"], [])
        ui_notice.clear()

    def test_event_channel_ui_wired(self):
        rp = (ROOT / "train_bot/run_party_digioi.py").read_text()
        self.assertIn('"event_channel_auto": False', rp)
        self.assertIn('"event_channel_manual": 0', rp)
        self.assertIn("def _chot_kenh_40npc(", rp)
        self.assertIn("def _bao_khong_du_cho_40npc(", rp)
        self.assertIn("def _event_channel_policy_active(", rp)
        ab = (ROOT / "agent_bridge.py").read_text()
        self.assertIn("def set_event_channel_policy_json(", ab)
        self.assertIn("def poll_ui_notices_json(", ab)
        base = Path(__file__).resolve().parents[1] / "app/src/main/java/com/fen/tsbot"
        amv = (base / "AccountManagerView.java").read_text()
        self.assertIn("renderLeaderEventChannelPolicy", amv)
        self.assertIn("refreshOpenChannelDropdowns", amv)
        self.assertIn("onEventChannelPolicy", amv)
        ma = (base / "MainActivity.java").read_text()
        self.assertIn("set_event_channel_policy_json", ma)
        self.assertIn("refreshUiNotices", ma)
        self.assertIn("poll_ui_notices_json", ma)

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

    def test_battle_arm_from_0x35_only_for_own_column(self):
        # 0x35 status-list mang CA 5 NGUOI trong party (hang 2/3 = phe ta). Neu CHI loc theo HANG,
        # tin hieu "toi luot" cua NGUOI KHAC (vd user ngoai vua duoc moi vao party) se arm bot SOM
        # -> bot gui lenh chua toi luot -> server tu choi -> khong gui lai -> tran doi HET GIO.
        # Phai loc them theo COT CUA MINH (`position[1] == my_atype`).
        source = (ROOT / "train_bot/client.py").read_text()
        a = source.index("def _track_battle_packet(")
        b = source.index("def _prepare_tracker_turn(", a)
        block = source[a:b]
        self.assertIn('event.position[0] in (config.UNIT_CHAR, config.UNIT_PET)', block)
        self.assertIn('event.position[1] == getattr(self.state, "my_atype", None)', block)

    def test_stale_combat_worker_self_heals_current_turn(self):
        # Worker cua luot CU bi vo hieu nhung luot HIEN TAI chua gui -> phai RE-ARM, khong duoc bo.
        # Truoc day chi `return` -> luot hien tai khong co worker nao -> bot dung im -> LUOT CHAM /
        # phai doi het gio (gap khi party co user ngoai / server doi luot nhanh).
        source = (ROOT / "train_bot/client.py").read_text()
        a = source.index("def _make_decisions(")
        b = source.index("def _send_combat(", a)
        block = source[a:b]
        self.assertIn("bo worker combat CU", block)
        self.assertIn("TU CHUA luot: worker cu bi vo hieu -> re-arm luot hien tai", block)
        self.assertIn("self._prepare_tracker_turn()", block)

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
