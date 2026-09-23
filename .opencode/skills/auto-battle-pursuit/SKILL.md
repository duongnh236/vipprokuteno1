---
name: AUTO BATTLE và AUTO TRUY KÍCH
description: Dùng khi làm việc với hai công tắc độc lập AUTO BATTLE (engine đánh + rule Pet & Skill) và AUTO TRUY KÍCH (chạy Ground path hình số 8) của ts_bot — bật/tắt, lưu theo account, quy tắc member không tự chạy, và các điều kiện chặn.
slash: true
metadata:
  opencode/autoinvoke: false
---

# AUTO BATTLE và AUTO TRUY KÍCH

> **MANUAL ONLY.** Skill này KHÔNG tự động được gọi. Chỉ load khi người dùng yêu cầu rõ ràng
> (bấm/gọi theo ID). Các workflow `farm-di-gioi`, `train-map`, `npc-40` **không** được tự gọi
> skill này. `metadata.opencode/autoinvoke: false` giữ nó ngoài danh sách model tự thấy; vẫn
> load thủ công được bằng ID `auto-battle-pursuit`.

Hai công tắc **ĐỘC LẬP** trên tab account:

- **AUTO BATTLE** — chỉ bật **engine đánh** và dùng setting **Pet & Skill**.
- **AUTO TRUY KÍCH** — chỉ chạy **Ground path hình số 8**; **tuyệt đối không** tự bật engine đánh.

Bật cái này **không** bật cái kia.

## Bật/tắt

| Việc | Chỗ code |
| --- | --- |
| Đảo công tắc (theo account) | `agent_bridge.set_auto_mode_json(username, mode)` (`mode` ∈ `battle`/`pursuit`) |
| Theo đúng slot UI | `agent_bridge.set_auto_mode_slot_json(slot, expected_username, mode)` |
| Lõi | `client.py::GameClient.apply_auto_mode(mode, enabled=None)` |
| Đồng bộ theo vùng | `client.py::sync_area_combat_mode(allow_pursuit=True)` |

`enabled=None` = người dùng bấm nút → **đảo** trạng thái hiện tại.

`apply_auto_mode` đặt:
- `_auto_battle_enabled`, `_auto_pursuit_enabled` (2 cờ độc lập);
- `auto_combat = battle`;
- `_dg_pursuit_paused = not pursuit`;
- `_auto_mode` = `both` / `battle` / `pursuit` / `off`.

## Khi bật AUTO BATTLE

- Nạp lại **Pet & Skill MỚI NHẤT** từ `config.ACCOUNT_BATTLE[username]` (không giữ snapshot cũ từ
  login) → `state.battle_config`.
- `flee_mode = False`.
- Nếu **không** đang trong trận: chạy `combat_ready()` trên **thread riêng** (gửi cả chuỗi setup
  `_login_setup`, ~2 giây) — **không** block nút UI. Công tắc đã BẬT ngay.

## Khi bật AUTO TRUY KÍCH

- `start_run_around(stay_in_di_gioi=False)` → thread `dg-pursuit-<user>` chạy `_run_around_loop`.
- Hình số 8: lấy vị trí hiện tại làm **anchor**, bám từng điểm theo `config.RUN_AROUND_OFFSETS`,
  mỗi bước qua `_bam_o_di_duoc` (Ground.mmg) rồi `navigate_to(..., require_smart_path=True)`.
- Chờ giữa bước: `RUN_STEP_WAIT`; đang đánh thì `RUN_RESUME_IDLE` rồi bỏ qua bước.
- `stop_run_around()` = tắt cờ `_running_route` + tăng `_run_around_generation` (hủy vòng đang chạy).

## Lưu theo account

- `agent_bridge` lưu `auto_battle_enabled` / `auto_pursuit_enabled` vào account settings (JSON) và
  `config.ACCOUNT_AUTO_MODE[username] = {"battle":…, "pursuit":…}`.
- Đặt `client._auto_flags_restored = True` để vòng account **không** restore snapshot cũ rồi ghi đè
  trạng thái vừa bấm.

## Quy tắc chặn (rất quan trọng)

- **Member trong party KHÔNG bao giờ tự chạy truy kích.** `follower = party_leader and
  party_leader != self_entity` → `sync_area_combat_mode` chuyển về `normal` và gọi `stop_run_around`.
- Truy kích bị chặn khi: `_daily_use_selected_pet`, `_daily_hold`, `_individual_safe_logout`,
  hoặc `allow_pursuit=False`.
- Không bịa tọa độ: không có `self.pos` hoặc không xác minh được ô đi được (Ground) → **không di
  chuyển**, log cảnh báo.
- `cancelled()` trong `_run_around_loop` hủy khi: tắt pursuit, đổi map, tăng generation, thành
  follower, daily hold, safe logout, hoặc mất kết nối.

## State / cờ

| Field | Ý nghĩa |
| --- | --- |
| `_auto_battle_enabled` / `_auto_pursuit_enabled` | 2 cờ độc lập |
| `auto_combat` | = `_auto_battle_enabled`; `_on_actions`/`_arm_decision` đọc cờ này để ra lệnh |
| `_auto_mode` | `both`/`battle`/`pursuit`/`off` |
| `_running_route` / `_run_around_generation` | vòng truy kích + thế hệ hủy |
| `_area_combat_mode` | `pursuit`/`normal` theo vùng |
| `_ui_auto_battle` | phản chiếu cho UI |
| `_dg_pursuit_paused` | pursuit tạm dừng (vd đang thoát DG) |
| `_auto_flags_restored` | chặn restore snapshot ghi đè nút vừa bấm |

## Liên hệ với combat

- Engine đánh dùng `state.battle_config` (rule Pet & Skill) — xem `combat.py::_battle_rules`.
- Chỉ khi `auto_combat=True` thì `_on_actions` mới gọi `_arm_decision` và mới gửi `0x32`.
- Workflow Train/Daily/DG **không** được tự bật đánh: `combat_ready` thoát nếu
  `_auto_battle_enabled` là False.

## Kiểm chứng

```bash
python3 -B -m unittest discover -s tests -q -p 'test_android_safety.py'
```

Test liên quan: `test_independent_daily_and_walk_combat`,
`test_pursuit_is_movement_only_and_stops_when_workflow_blocks_it`,
`test_dg_pursuit_requires_ground_and_generation`,
`test_selected_pet_wins_across_all_workflows_with_default_fallback`.
