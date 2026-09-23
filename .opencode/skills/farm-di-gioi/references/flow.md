# Luồng chi tiết: Dị Giới -> Train

Nguồn chuẩn: `docs/android-workflows.md` (mục "Dị giới + Train theo map") và
`docs/workflow-architecture.md`. File này tóm tắt để tra cứu nhanh trong skill.

## 0. Bắt đầu

- Entry: `agent_bridge.start_farm_mode_json(mode, map_id, x, y, di_gioi_level)`.
- Với DG: chốt account online, **lưu riêng mục tiêu farm** (`ui_dg_train_target`), chuyển runtime
  vào DG. Trạng thái "chưa biết / đang reconnect" **không** được coi là đã hết giờ DG.
- Account xong trước ra **điểm chờ**.

## 1. Thoát Dị Giới

- DG **không có lệnh thoát**: phải **đi bộ tới cổng `(270, 210)`** (`GameClient.DIGIOI_CONG_RA`),
  tới cổng map tự đổi.
- `GameClient.exit_di_gioi()`:
  - `_dg_pursuit_paused = True`, `stop_run_around()`, `flee_mode = True` (đi đường thoát thì né
    trận, không dừng đánh).
  - Ưu tiên smart path `navigate_to(270, 210, flee=True)`; fallback chuỗi 7 bước từ capture
    (`_di_bo_chuoi_buoc_ra_cong`).
  - Gửi `0x14 08000100` → `0x0c 0100` → `0x14 0600`, rồi kiểm tra thoát bằng `_left_di_gioi()`
    (đọc `current_map`, KHÔNG dựa số kênh).
  - **Không bỏ cuộc**: kẹt trong DG là kẹt vĩnh viễn. Chỉ dừng khi đã ra, hoặc acc STOP / rớt mạng.
- Điều kiện "đã sẵn sàng": `client.in_di_gioi()` trả `False` và
  `client._dg_train_ready_token == token` của lệnh hiện tại.

## 2. Về thành gần bãi

- Thành gần bãi: `GameClient.nearest_smart_city(dest_map, exclude_map=dest_map)` (dữ liệu smart route).
- Về thành: `GameClient.go_to_town(city, flag)`.
- **Không** teleport trung gian random, **không** bán/cất đồ trong bước này (khác `pre_route_town_hop`
  của luồng đi train thường).
- Chờ **đủ** account được **server xác nhận** tới thành: `_wait_manual_city_arrived(expected)`
  đọc `manual_route_city_arrived`.

## 3. Gôm party tại thành

- Leader công bố **phân khu live** tại thành; member chuyển tới đúng phân khu
  (`switch_channel(...)`).
- Member: `set_party_invite_ready(True)` **trước** khi chờ leader.
- Leader: `invite_members(gap=...)` → kiểm tra **đúng entity** từng member trong roster server
  (`party_members`), cùng map + cùng phân khu.
- Đủ đội: `set_party_strategist()`.

## 4. Ra bãi train

- **Chỉ leader** chạy `navigate_to(x, y, ...)` / `follow_smart_route(...)` ra map train tới tọa độ.
- Member theo party; combat bật trên đường, dùng rule đã cấu hình.
- Xong: `ui_train_phase = "farming"`.

## Handoff DG -> Train

`workflows/digioi.py::_android_dg_train_handoff(pidx, st)`:

1. Đặt `ui_dg_handoff_started`, `ui_dg_transition_pending`, `ui_dg_transition_token = cmd_gen`.
2. `PARTY_CONFIG[pidx].update(mode="stand", start_city_id=0)`.
3. Thread `dg-train-handoff` chờ tới khi **mọi** user trong party:
   - `client.running`
   - `not client.in_di_gioi()`
   - `client._dg_train_ready_token == token`
4. Đủ + leader online → `manual_train_users`, `stop_run_around()`, `flee_mode = False`,
   rồi phát **đúng một** lệnh: `party_train_map(pidx, *target, expected_generation=token)`.

## State / cờ cần soi khi kẹt

| Field | Ý nghĩa |
| --- | --- |
| `ui_train_phase` | `gather` → ... → `farming` |
| `ui_dg_train_target` | mục tiêu train lưu riêng cho handoff |
| `ui_dg_handoff_started` / `ui_dg_transition_pending` / `ui_dg_transition_token` | trạng thái handoff |
| `manual_train_users` | danh sách account của team train |
| `manual_route_plan` / `manual_route_plan_ready` | leader đã lập kế hoạch route |
| `manual_route_city_arrived` | account đã được xác nhận tới thành |
| `manual_route_source_results` / `manual_route_source_done` | report "đang ở map nguồn" |
| `manual_route_party_ready` / `manual_route_done` | mốc party sẵn sàng / route xong |
| `ui_member_recover` / `ui_leader_recover` / `ui_recovery_safe_ready` | phục hồi member / leader |
| `cmd_gen` | generation lệnh; lệnh mới hủy đường đi generation cũ |

## Bẫy đã từng gặp

- Gửi packet khi đang giữ `st["lock"]` → deadlock/cập nhật roster đồng bộ.
- Không kiểm tra `cmd_gen` sau `wait` → thread lệnh cũ quay lui generation, xóa report của lệnh mới.
- Đoán "đã tới thành/đã hết DG" theo đồng hồ thay vì theo xác nhận server.
- Tự relogin chỉ vì không gặp quái (làm kẹt vòng đăng nhập khi server chặn tốc độ login).
- Coi account reconnect/chưa biết là "đã xong DG" → handoff sớm.
