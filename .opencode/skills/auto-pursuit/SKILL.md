---
name: AUTO TRUY KÍCH
description: Dùng khi làm việc với công tắc AUTO TRUY KÍCH của ts_bot — chạy Ground path hình số 8, bật/tắt, lưu theo account, member không tự chạy, điều kiện chặn, và hành vi khi gặp trận (đứng yên chờ, không đi tiếp).
slash: true
metadata:
  opencode/autoinvoke: false
---

# AUTO TRUY KÍCH

> **MANUAL ONLY.** Skill này KHÔNG tự động được gọi. Chỉ load khi người dùng yêu cầu rõ ràng
> (gõ `/auto-pursuit` hoặc gọi theo ID). Các workflow `farm-di-gioi`, `train-map`, `npc-40`,
> `di-gioi`, `daily` **không** được tự gọi skill này. `metadata.opencode/autoinvoke: false` giữ nó
> ngoài danh sách model tự thấy; vẫn load thủ công được bằng ID `auto-pursuit`.

**AUTO TRUY KÍCH** chỉ chạy **Ground path hình số 8**; **tuyệt đối KHÔNG** tự bật engine đánh
(engine đánh là skill `auto-battle`). Hai công tắc **độc lập**.

## Bật/tắt

| Việc | Chỗ code |
| --- | --- |
| Đảo công tắc (theo account) | `agent_bridge.set_auto_mode_json(username, "pursuit")` |
| Theo đúng slot UI | `agent_bridge.set_auto_mode_slot_json(slot, expected_username, "pursuit")` |
| Lõi | `client.py::GameClient.apply_auto_mode("pursuit", enabled=None)` |
| Đồng bộ theo vùng | `client.py::sync_area_combat_mode(allow_pursuit=True)` |
| Vòng chạy | `client.py::start_run_around` / `stop_run_around` / `_run_around_loop` |

`apply_auto_mode("pursuit")` đặt `_auto_pursuit_enabled`, `_dg_pursuit_paused = not pursuit`, rồi
`start_run_around(stay_in_di_gioi=False)` (hoặc `stop_run_around()` khi tắt).

## Hình số 8

- Lấy vị trí hiện tại làm **anchor**, bám từng điểm theo `config.RUN_AROUND_OFFSETS`
  (`[(-100,-100),(-200,0),(-100,100),(0,0),...]`).
- Mỗi bước qua `_bam_o_di_duoc` (Ground.mmg) rồi `navigate_to(..., flee=False,
  require_smart_path=True)`.
- Chờ giữa bước: `RUN_STEP_WAIT` (0.70s).
- Tâm run-around DG: `_di_gioi_anchor` (điểm tele vào, cố định, tránh rìa map sau relogin).

## Khi gặp trận — ĐỨNG YÊN CHỜ, KHÔNG đi tiếp

- Đầu mỗi bước: `if self.in_combat(RUN_RESUME_IDLE=2.0): self._soi_luot_cham(); sleep(0.3); continue`
  → **không mở bước mới**.
- Giữa đường (`navigate_to`): `if self.in_combat(1.0): sleep(0.5); continue` → **ngừng gửi lệnh
  move**; thời gian chờ **không** tính vào `max_iter`; kẹt 1 trận quá `NAV_CHO_TRAN_CAP=180s` → bỏ chặng.
- Khớp client game: `MoveController:Update()` return khi `FightField.isInBattle` (không gửi
  `C:006-001`) → nhân vật đứng yên.
- Hết trận mới đi tiếp **đúng bước đang dở** (KHÔNG bỏ qua bước).
- `_soi_luot_cham()` chỉ **ghi log chẩn đoán** (ai đã gửi lệnh đánh, lượt kéo bao lâu) — **không**
  di chuyển.
- → "vừa đánh vừa chạy" là **không** xảy ra. Muốn có đánh trong lúc đó phải bật **AUTO BATTLE**
  (skill `auto-battle`).

## Quy tắc chặn (rất quan trọng)

- **Member trong party KHÔNG bao giờ tự chạy truy kích.** `follower = party_leader and
  party_leader != self_entity` → `sync_area_combat_mode` chuyển `normal` + `stop_run_around`.
- Truy kích bị chặn khi: `_daily_use_selected_pet`, `_daily_hold`, `_individual_safe_logout`,
  hoặc `allow_pursuit=False`.
- Không bịa tọa độ: không có `self.pos` hoặc không xác minh được ô đi được (Ground) → **không di
  chuyển**, log cảnh báo.
- `cancelled()` trong `_run_around_loop` hủy khi: tắt pursuit, đổi map, tăng generation, thành
  follower, daily hold, safe logout, hoặc mất kết nối.

## State / cờ

| Field | Ý nghĩa |
| --- | --- |
| `_auto_pursuit_enabled` | công tắc AUTO TRUY KÍCH |
| `_running_route` / `_run_around_generation` | vòng truy kích + thế hệ hủy |
| `_area_combat_mode` | `pursuit`/`normal` theo vùng |
| `_dg_pursuit_paused` | pursuit tạm dừng (vd đang thoát DG) |
| `_di_gioi_anchor` | tâm run-around DG |
| `_auto_mode` | `both`/`battle`/`pursuit`/`off` |

## Lưu theo account

- `agent_bridge` lưu `auto_pursuit_enabled` vào account settings (JSON) và
  `config.ACCOUNT_AUTO_MODE[username]["pursuit"]`.
- Relogin: vòng account đọc `ACCOUNT_AUTO_MODE` → `apply_auto_mode("pursuit", saved)`.

## Kiểm chứng

```bash
python3 -B -m unittest discover -s tests -q -p 'test_android_safety.py'
```
Test liên quan: `test_pursuit_is_movement_only_and_stops_when_workflow_blocks_it`,
`test_dg_pursuit_requires_ground_and_generation`.
