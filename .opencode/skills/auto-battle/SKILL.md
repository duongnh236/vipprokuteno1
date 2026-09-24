---
name: AUTO BATTLE
description: Dùng khi làm việc với công tắc AUTO BATTLE của ts_bot — bật/tắt engine đánh + dùng setting Pet & Skill, lưu theo account, re-arm combat-active, các điều kiện chặn, và vì sao vào trận mà không đánh.
slash: true
metadata:
  opencode/autoinvoke: false
---

# AUTO BATTLE

> **MANUAL ONLY.** Skill này KHÔNG tự động được gọi. Chỉ load khi người dùng yêu cầu rõ ràng
> (gõ `/auto-battle` hoặc gọi theo ID). Các workflow `farm-di-gioi`, `train-map`, `npc-40`,
> `di-gioi`, `daily` **không** được tự gọi skill này. `metadata.opencode/autoinvoke: false` giữ nó
> ngoài danh sách model tự thấy; vẫn load thủ công được bằng ID `auto-battle`.

**AUTO BATTLE** là công tắc **bật engine đánh** và dùng setting **Pet & Skill**. Nó **ĐỘC LẬP** với
**AUTO TRUY KÍCH** (di chuyển hình số 8 — skill `auto-pursuit`). Bật cái này **không** bật cái kia.

## Bật/tắt

| Việc | Chỗ code |
| --- | --- |
| Đảo công tắc (theo account) | `agent_bridge.set_auto_mode_json(username, "battle")` |
| Theo đúng slot UI | `agent_bridge.set_auto_mode_slot_json(slot, expected_username, "battle")` |
| Lõi | `client.py::GameClient.apply_auto_mode("battle", enabled=None)` |

`enabled=None` = người dùng bấm nút → **đảo** trạng thái hiện tại.

`apply_auto_mode("battle")` đặt:
- `_auto_battle_enabled` (đảo), `_ui_auto_battle`;
- `auto_combat = _auto_battle_enabled` ← **cờ DUY NHẤT quyết định có gửi lệnh đánh**;
- `flee_mode = False` (không bỏ chạy);
- nạp lại **Pet & Skill MỚI NHẤT** từ `config.ACCOUNT_BATTLE[username]` → `state.battle_config`;
- nếu **không** đang trong trận: chạy `combat_ready()` trên **thread riêng** (gửi chuỗi setup
  `_login_setup` ~2 giây) — **không** block nút UI.

## Engine đánh hoạt động thế nào

- Chỉ khi `auto_combat=True` thì khi có gói "tới lượt" (`0x35`/`0x34`) mới gọi `_arm_decision()`
  → `_make_decisions()` → gửi `0x32`. `auto_combat=False` → **không gửi lệnh đánh**.
- Rule skill lấy từ `state.battle_config` — xem `combat.py::_battle_rules`.
- 2 đường nhận lượt:
  - **Legacy** (`battle_tracker.generation == 0`): `_on_actions` (0x35) — arm khi record
    `skill_id=0` ở hàng char/pet.
  - **Tracker** (mặc định): `_prepare_tracker_turn()` gọi ở `turn_start` (0x34) **và** ở sự kiện
    `status` của 0x35 (arm lại để không phụ thuộc THỨ TỰ gói — xem mục dưới).

## An toàn vòng đời lượt

- Mỗi decision worker của tracker phải chốt khóa bất biến `(generation, turn)` và một snapshot
  riêng của `available` ngay lúc arm. Không được để worker đọc `tracker.turn` hoặc `available`
  đang thay đổi trong lúc chạy.
- Trước **mỗi** lệnh `0x32`, `_send_combat(..., expected_key=...)` phải xác nhận khóa vẫn là lượt
  hiện tại. Worker cũ chỉ được ghi log rồi thoát; không được gửi lệnh, xóa option hoặc reset state
  của lượt mới.
- Với tracker, trạng thái “đã đánh” chỉ được mở lại bởi `turn_start` (`0x34`) của lượt mới. Timer
  reset cũ không được mở lại cùng một lượt; nếu không, `0x35` tới sớm có thể arm nhầm dưới số
  lượt cũ.
- Dị giới solo nhiều pet và party team dùng chung invariant này. Không vá riêng workflow Dị giới;
  lỗi thuộc vòng đời combat cấp thấp trong `client.py`.

## Vì sao "vào trận mà KHÔNG đánh"

Bot đứng im dù đã bật AUTO BATTLE khi:
- `_auto_battle_enabled`/`auto_combat` thực ra **đang tắt**. UI có thể hiện ON do **optimistic**
  (`localAutoBattle` trong `AccountManagerView`): nếu lệnh bấm lỗi (account chưa online, slot lệch)
  thì UI vẫn ON nhưng server OFF → không đánh.
- **`flee_mode=True`** và **không có party** (`party_members` rỗng): `_make_decisions` **bỏ chạy**
  thay vì đánh. Workflow có thể set `flee_mode=True` (đang gom party, chưa có quân sư, đứt trận…).
  Trong party (`party_members` non-empty) thì `flee_mode` bị bỏ qua → vẫn đánh.
- `_prepare_tracker_turn` **không có option** (`available` rỗng): targets rỗng (hết quái sống), hoặc
  unit của mình chưa có trong tracker, hoặc `my_atype` sai. Log sẽ có dòng
  `BATTLE g=.. t=..: KHONG co option (targets=.., my_atype=.., char_unit=.., pet_unit=.., enemy_rows=..)`.
- **DG solo (`state.solo_multipet=True`)**: 4 pet ra trận **cùng lượt**, mỗi con 1 `atype` riêng
  (0/1/3/4). Engine phải gom option cho **CẢ 4** atype pet (KHÔNG lọc theo `my_atype` của char —
  xem `_prepare_tracker_turn` + `_make_decisions` nhánh `solo_multipet`). Thiếu → pet không ra lệnh
  → trận kẹt, nhìn như "đang chờ lệnh đánh từ pet".
- `_gate_transit` (đang qua cổng) → hoãn lượt.
- `_acted_turn` còn True / `_in_battle_end_grace()` (vừa kết trận thật) → bỏ lượt.

`combat_ready()` **thoát ngay (no-op)** nếu `_auto_battle_enabled` là False → workflow Train/Daily/DG
**không** tự bật đánh.

## Lưu theo account

- `agent_bridge` lưu `auto_battle_enabled` vào account settings (JSON) và
  `config.ACCOUNT_AUTO_MODE[username]["battle"]`.
- Đặt `client._auto_flags_restored = True` để vòng account **không** restore snapshot cũ ghi đè nút
  vừa bấm.
- Relogin: vòng account đọc `ACCOUNT_AUTO_MODE` → `apply_auto_mode("battle", saved)`.

## State / cờ

| Field | Ý nghĩa |
| --- | --- |
| `_auto_battle_enabled` | công tắc AUTO BATTLE |
| `auto_combat` | = `_auto_battle_enabled`; `_on_actions`/`_prepare_tracker_turn` đọc để arm |
| `_ui_auto_battle` | phản chiếu cho UI + điều kiện `should_fight` (re-arm keepalive) |
| `_auto_mode` | `both`/`battle`/`pursuit`/`off` |
| `_acted_turn` | đã ra lệnh cho lượt này chưa |
| `_in_battle_end_grace()` | vừa kết trận thật → không ra lệnh |
| `flee_mode` | True = vào trận thì BỎ CHẠY (chỉ khi không có party) |

## Liên hệ

- Di chuyển khi farm: skill `auto-pursuit` (AUTO TRUY KÍCH).
- Workflow Train/Daily/DG **không** được tự bật đánh: `combat_ready` thoát nếu `_auto_battle_enabled` False.

## Kiểm chứng

```bash
python3 -B -m unittest discover -s tests -q -p 'test_android_safety.py'
```
Test liên quan: `test_independent_daily_and_walk_combat`,
`test_selected_pet_wins_across_all_workflows_with_default_fallback`,
`test_combat_worker_is_pinned_to_generation_and_turn_for_solo_and_team`.
