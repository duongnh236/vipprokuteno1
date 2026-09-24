# Daily — danh sách task & chi tiết

Nguồn: `workflows/daily.py`, `agent_bridge.run_daily_tasks_json` / `daily_status_json`,
`run_party_digioi.py` (nhánh `daily`).

## Nhãn task

| id | Nhãn |
| --- | --- |
| `legion_boss` | Boss quân đoàn |
| `world_boss` | Boss thế giới |
| `solo_dungeon` | Phụ bản đơn |
| `team_dungeon` | Phụ bản tổ đội |
| `team_dungeon_20` | Thảo Phạt Thiên Sư • Cấp 20 |
| `team_dungeon_50` | Ngày Tàn Hoạn Quan • Cấp 50 |
| `team_dungeon_80` | Đại Chiến Lữ Bố • Cấp 80 |
| `team_dungeon_110` | Hỏa Thiêu Bộc Dương • Cấp 110 |

## Thứ tự & gộp

- Thứ tự cố định: **PB đội → `legion_boss` → `solo_dungeon` → `world_boss`**.
- Nếu có bất kỳ `team_dungeon*` nào → gộp thành **một** id `team_dungeon`; các cấp 20/50/80/110 là
  tham số (`team_levels`), gán vào `team_dungeons` của config. **Không** chạy ba task riêng (worker
  cũ có thể vượt barrier và chạy boss trong lúc leader còn gom phòng).

## Chuẩn bị (mỗi acc độc lập)

`_daily_return_to_city(c, username, stopped_fn)`:
1. `_workflow_leave_current_area(c, stopped_fn)` — dừng combat / rời vùng an toàn.
2. `set_account_activity(..., "Daily: phu ve Trac Quan", phase="daily")`.
3. `go_to_town(12001, 0, tries=5, wait=2.0, battle_grace=0.0)`.
4. Xác nhận `current_map == 12001`; sai → `RuntimeError("Chưa được server xác nhận tới Trác Quận")`.
5. `flee_mode = False`; `combat_ready()` (chỉ tác dụng nếu user đã bật AUTO BATTLE).
- Lỗi → log cảnh báo + **giữ online** + `phase="wait"`; caller đặt `_daily_instance_blocked = True`.

## Pet

Daily dùng **pet người dùng đã chọn** trong Pet & Skill: `_ui_selected_pet_id` → `switch_pet(id)`
trước khi chạy task (`_daily_use_selected_pet = True`). Cuối lượt trả `False`.

## Task PB đội

- Cần **leader online**; nếu leader offline → `raise ValueError("Leader phải online ...")`.
- Config cho lượt daily: `auto_team_dungeon=True`, `manual_daily_barrier_done=True`,
  `team_dungeons = {20/50/80/110: bool}`.
- `_manual_team_dungeon_rally(c, st, username, pidx, daily_stopped)`: tập trung đủ đội tại Trác Quận
  (không ép cùng phân khu), leader tạo phòng + mời; thất bại → `daily_team_rally_error`.
- `_run_auto_team_dungeons_if_needed(...)`: chạy phó bản theo cơ chế ready của server.
- Generation riêng: `daily_team_generation` — lệnh Daily mới **hủy ngay** worker PB đội cũ (tránh
  member chạy boss trong lúc leader gom phòng).
- `c._td_stop_requested = lambda: bool(st.get("daily_cancel"))` để PB đội dừng theo Daily.

## Hàng rào giữa task

- Sau mỗi task: `daily_step_done["%d:%s" % (index, task)]` thêm username; `daily_resume_indices[user] = index+1`.
- Task **không phải** `team_dungeon` → đi tiếp ngay (không chờ ai).
- Task `team_dungeon` → chờ tới khi `daily_participants ⊆ daily_step_done[step_key]` (tối đa 20 phút
  rồi đi tiếp kèm cảnh báo).
- Acc rớt giữa task: **không** tính là task xong; `daily_resume_indices` cho chạy tiếp sau relogin.

## Trạng thái & đếm lượt

`daily_status_json` đọc từ client:
- `legion_boss_current/max/next` (RoleCount `0x55` id `0x2a`).
- `world_boss_current/max` (mission step `12207`).
- `solo_dungeon_remaining()` / `team_dungeon_remaining(level)`.
- `in_battle`, `activity`.

## Phase

`daily_phase`: `queued` → `running` → `completed` / `cancelled` / `failed` / `stopping`.
- `completed`: đứng yên giữ online; `daily_hold_after_stop = True`.
- `cancelled`: dừng sau trận hiện tại, đứng yên giữ online, **không logout**.
- `failed`: `daily_error` hoặc `daily_team_rally_error`.

## Lưu ý

- Daily **thu hồi** farm/DG: reset `ui_train_target`, `ui_dg_train_target`, `reform_gen_thoa`, kênh,
  `nhip_acc`, cache `team_dungeon_state` của lượt trước.
- Sau Daily muốn farm lại phải bấm **Bắt đầu farm** — không tự quay lại.
- Không giả lập điều kiện/lượt; điều kiện theo server.
