---
name: Daily
description: Dùng khi làm việc với luồng Daily quest của ts_bot — chạy các task boss quân đoàn, boss thế giới, phụ bản đơn, phụ bản tổ đội; chuẩn bị về Trác Quận độc lập từng acc; hàng rào task đội; dừng Daily an toàn; và báo trạng thái.
---

# Daily

Daily là một workflow **tường minh** của Android: người dùng tick task rồi bấm chạy. Nó **thu hồi**
mục tiêu farm/Dị Giới và dừng điều phối farm. Mỗi account chạy task solo **độc lập**; chỉ **phụ bản
tổ đội** là workflow chung do leader sở hữu.

## Task hợp lệ

`legion_boss`, `world_boss`, `solo_dungeon`, `team_dungeon` (hoặc `team_dungeon_20/50/80/110`).

**Thứ tự cố định**: PB đội trước → `legion_boss` → `solo_dungeon` → `world_boss`. Không phát
20/50/80 thành ba task riêng — PB đội là **một** workflow chung, các cấp là tham số.

## Luồng

1. **Bắt đầu** — `agent_bridge.run_daily_tasks_json(tasks_json)` → `party_daily_tasks` →
   `workflows/daily.py::party_daily_tasks`:
   - Thu hồi `ui_train_target`, `ui_dg_train_target`, dừng gom/reform (`reform_gen_thoa`), reset
     cache `team_dungeon_state` của lượt trước.
   - `PARTY_CONFIG.update(mode="stand", do_daily=False, ...)`; đặt `daily_active=True`, `cmd=("daily", chosen)`.
   - **PB đội cần leader online**; nếu không → báo lỗi ngay.
2. **Chuẩn bị** — mỗi acc tự `_daily_return_to_city` (`workflows/daily.py`):
   - `_workflow_leave_current_area` (dừng combat/rời vùng an toàn) → `go_to_town(12001)` (Trác Quận).
   - **Không** chờ team; xác nhận bằng `current_map == 12001` (server), không đoán.
   - `flee_mode = False`; `combat_ready()` (chỉ có tác dụng nếu user đã bật AUTO BATTLE).
   - Lỗi giữa chừng → **giữ online**, log, `_daily_instance_blocked = True`.
3. **Chạy task** — dùng **pet đã chọn** trong Pet & Skill (`_daily_use_selected_pet`, `switch_pet`),
   rồi duyệt task:
   - `legion_boss` / `world_boss` → `workflows/boss.py::run_selected`.
   - `solo_dungeon` → `client.do_daily_dungeon`.
   - `team_dungeon*` → `_manual_team_dungeon_rally` + `_run_auto_team_dungeons_if_needed` (leader
     tạo phòng/mời; member nhận lời; chỉ start theo cơ chế ready của phó bản).
4. **Hàng rào giữa task** — sau mỗi task ghi `daily_step_done[step_key]`. **Chỉ task
   `team_dungeon`** mới chờ đủ `daily_participants`; task solo không có hàng rào team. Hàng rào PB
   đội tối đa 20 phút rồi đi tiếp (log cảnh báo).
5. **Kết thúc** — hết `daily_pending` → `daily_phase = completed` (hoặc `cancelled`), **đứng yên
   giữ online**. Lỗi → `daily_phase = failed`, giữ online.

## Dừng Daily

- `agent_bridge.stop_daily_json()` → `party_stop_daily(0)`:
  - `daily_cancel = True`, `daily_phase = "stopping"`, mọi acc `_daily_hold = True`, `_ui_auto_battle = False`.
  - Callback boss/dungeon kết thúc **sau trận đang đánh** → **không logout**.
- Sau khi dừng: đứng yên giữ online. **Không** tự quay lại farm/DG; muốn farm thì bấm Bắt đầu farm lại.

## Trạng thái

`agent_bridge.daily_status_json()` trả: `daily_active`, `daily_tasks`, `daily_task`, `daily_phase`,
`daily_user`, `daily_message`, `daily_started_at`, `daily_warnings`, và per-acc:
`legion_boss_current/max/next`, `world_boss_current/max`, `solo_dungeon_remaining`,
`team_dungeon_remaining`, `in_battle`, `activity`.

Field nội bộ trong `st`: `daily_pending`, `daily_participants`, `daily_step_done`,
`daily_resume_indices` (chạy tiếp sau relogin), `daily_team_*`, `daily_cancel`, `daily_hold_after_stop`.

## Đánh trong Daily — KHÔNG tự động

Daily **không** tự bật engine đánh. Việc đánh do công tắc **AUTO BATTLE** của user quyết định — chi
tiết ở skill `auto-battle` (manual, chỉ user gọi; xem mục AUTO BATTLE).

- `_daily_return_to_city` có gọi `combat_ready()`, nhưng đây chỉ là **re-arm**: hàm **thoát ngay
  (no-op) nếu `_auto_battle_enabled` đang tắt** (`workflows/daily.py:23`, xem `client.combat_ready`).
- `_auto_battle_enabled = True` **chỉ** được set trong `apply_auto_mode` (`client.py`), gọi từ
  `agent_bridge.set_auto_mode_json` (nút bấm của user) hoặc restore từ setting đã lưu.
- Dừng Daily đặt `_ui_auto_battle = False`; đây là cờ hiển thị/theo workflow, **khác** engine
  (`_auto_battle_enabled` + `auto_combat`) — dừng Daily không tự đổi engine thay user.

→ **Chưa bật AUTO BATTLE thì acc trong Daily đứng yên, không tự đánh.**

## Quy tắc

- PB đội chạy **trước** daily solo.
- Task solo **không** chờ team; PB đội là barrier riêng.
- Lỗi teleport / phòng không hợp lệ → log + **giữ online**, không giả lập đủ điều kiện/lượt.
- Điều kiện level/lượt theo **server**; không ACK thành công thay server.
- Daily chạy xong/dừng → đứng yên; không tự về farm.
- Leader offline → không chạy được PB đội (báo lỗi, không treo).

## Điểm vào code

| Việc | Chỗ code |
| --- | --- |
| Entry Android | `agent_bridge.run_daily_tasks_json` / `daily_status_json` / `stop_daily_json` |
| Setup daily | `workflows/daily.py::party_daily_tasks` |
| Về thành | `workflows/daily.py::_daily_return_to_city` |
| Boss | `workflows/boss.py::run_selected` |
| PB đơn | `client.py::do_daily_dungeon` |
| PB đội | `run_party_digioi.py::_manual_team_dungeon_rally`, `_run_auto_team_dungeons_if_needed` |
| Dừng | `run_party_digioi.py::party_stop_daily` |
| Vòng xử lý | `run_party_digioi.py` (~7580–7740, nhánh `daily`) |

Danh sách task + handler chi tiết: `references/tasks.md`.

## Kiểm chứng

```bash
python3 -B -m unittest discover -s tests -q -p 'test_android_safety.py'
```

Test liên quan: `test_daily_city_preparation_is_independent_and_keeps_online_on_failure`,
`test_daily_recovery_does_not_disconnect`, `test_independent_daily_and_walk_combat`.

Nguồn chuẩn: `docs/android-workflows.md` (mục Daily quest).
