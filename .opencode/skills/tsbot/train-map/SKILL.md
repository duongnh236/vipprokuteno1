---
name: Train theo map
description: Dùng khi làm việc với luồng Train theo map (không phải Farm + Dị Giới) — gom party, chọn thành gần bãi, đồng bộ phân khu, leader chạy ra điểm train, bật combat. Gồm cả phục hồi member/leader, fallback kênh đầy và phân khu.
---

# Train theo map

Mục tiêu: từ lệnh Bắt đầu farm, **gom đủ party → về thành gần map train → đồng bộ phân khu →
leader chạy smart route ra bãi → bật combat**. Member theo party, dùng rule skill/HP/SP đã lưu.

Khác `farm-di-gioi`: luồng này **không** có pha Dị Giới. Nếu đang farm DG rồi mới sang train, xem
skill `farm-di-gioi`.

## Luồng (thứ tự bắt buộc)

1. Chốt account đang online khi bấm Bắt đầu farm; **leader phải online**.
2. Leader chọn thành gần map train bằng dữ liệu smart route, công bố **cùng một kế hoạch** cho member.
3. Mỗi account đánh xong trận: dừng di chuyển Dị giới nếu có, thoát DG/rời party cũ, phù về thành đã
   chọn. **Không** teleport trung gian random, **không** bán/cất đồ ở bước này.
4. Chờ đủ account được **server xác nhận** đã tới thành. Leader công bố **phân khu live** tại thành;
   member chuyển tới đúng phân khu đó.
5. Member **mở nhận lời mời trước** khi chờ leader. Leader mời và kiểm tra **đúng entity** từng
   member trong roster server (cùng map + cùng phân khu). Đủ đội → chọn quân sư.
6. **Chỉ leader** chạy smart route/Ground path ra map train rồi tới tọa độ. Member theo party.
7. Thành công: `ui_train_phase = "farming"`. Thất bại: giữ online, log lý do, **không** chạy tiếp một
   mình, **không** tự relogin chỉ vì không gặp quái.

## Điểm vào trong code

| Việc | Chỗ code |
| --- | --- |
| Entry Android | `agent_bridge.start_farm_mode_json('train', map_id, x, y)` |
| Bắt đầu team | `agent_bridge.auto_battle_team_json(map_id, x, y)` |
| Lệnh train | `workflows/train.py::party_train_map(pidx, map_id, x, y)` |
| Chạy route + phân khu | `run_party_digioi.py::_do_manual_cmd('train')` → `_do_manual_route()` |
| Ra bãi | leader `GameClient.navigate_to(x, y, ...)` |
| Phục hồi member/leader | `workflows/train.py::_android_train_recovery_tick` |
| Phân khu đầy / retry | `workflows/train.py::_train_retry_leader_channel`, `_train_fallback_full_channel` |
| Đổi map ⇒ bỏ ghim kênh | `workflows/train.py::_train_adopt_map_channel` |
| Member mở nhận lời mời | `workflows/train.py::_open_route_member_invites` |
| Gom lại do lệch kênh | `workflows/channel_regroup.py::request/tick` |
| Roster party | `workflows/party.py::missing_from_server_roster` |

## State / cờ cần soi khi kẹt

| Field | Ý nghĩa |
| --- | --- |
| `ui_train_target` | `(map, x, y)` mục tiêu train |
| `ui_train_phase` | `gather` → ... → `farming` (hoặc `regroup`) |
| `manual_train_users` | danh sách account của team |
| `manual_train_expected` / `n_members` | số kỳ vọng / số member |
| `manual_train_channel` / `manual_train_channel_ready` | phân khu đích + ai đã vào |
| `kenh_dich` / `kenh_ghim` | kênh đích / kênh đang ghim |
| `train_channel_map` | kênh thuộc 1 map; qua cổng phải bỏ ghim |
| `manual_route_plan` / `manual_route_plan_ready` | leader đã lập kế hoạch route |
| `manual_route_city_arrived` / `manual_route_source_results` | tới thành / report map nguồn |
| `manual_route_party_ready` / `manual_route_done` | party sẵn sàng / route xong |
| `ui_member_recover` / `ui_leader_recover` / `ui_recovery_safe_ready` / `ui_recovery_city_arrived` | phục hồi |
| `ui_kicked_users` | account bị server kick (không reconnect) |
| `cmd_gen` | generation lệnh; lệnh mới hủy đường đi generation cũ |

## Quy tắc khi sửa

- **KHÔNG gửi/nhận packet khi đang giữ `st["lock"]`** — xử lý invite có thể cập nhật roster đồng bộ.
- Sau mọi `wait`/hành động mạng, kiểm tra lại **session cancellation** và **`cmd_gen`**.
- Chỉ **leader** chạy route; member **tuyệt đối không** tự phát lệnh di chuyển.
- Không còn fast-path "bỏ về thành khi đã ở map train"; generation mới hủy đường đi cũ.
- Phân khu manual phải áp dụng **ngay tại thành tập kết**, trước khi mời party và kéo ra bãi.
- Tái dùng battle/heal config đã lưu, **không** ghi đè rule skill / ngưỡng HP/SP khi chuyển luồng.
- Feature mới → module riêng + entry point riêng (`docs/workflow-architecture.md`).

## Kiểm chứng

```bash
python3 -B -m unittest discover -s tests -q -p 'test_android_safety.py'
python3 -B -m unittest discover -s tests -q -p 'test_workflow_architecture.py'
python3 -B -m unittest discover -s tests -q -p 'test_channel_regroup.py'
python3 -B -m unittest discover -s tests -q -p 'test_city_exit.py'
```

Test liên quan trực tiếp: `test_full_train_command_gathers_five_then_routes_only_leader`,
`test_train_members_never_advance_gate_events_on_their_own`,
`test_farm_requires_exact_server_roster`,
`test_farming_channel_change_queues_safe_flow_not_direct_switch`,
`test_full_channel_fallback_requires_fresh_capacity_for_entire_team`,
`test_leader_loss_returns_members_to_city_before_restart`,
`test_member_catches_up_at_safe_then_leader_picks_up_without_team_restart`.

Kiểm thử logic, **không thay thế lượt test online**. Nguồn chuẩn: `docs/android-workflows.md`.
