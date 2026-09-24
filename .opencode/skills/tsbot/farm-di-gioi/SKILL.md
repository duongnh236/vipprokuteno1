---
name: Farm + Dị Giới
description: Dùng khi làm việc với luồng farm Dị Giới rồi chuyển sang train — thoát Dị Giới, về thành gần bãi, leader gôm party, cả đội chạy ra điểm train. Gồm cả việc sửa/thêm bước trong handoff DG -> Train của ts_bot.
---

# Farm + Dị Giới (DG -> Train handoff)

Mục tiêu: sau khi farm xong **Dị Giới**, mỗi account tự ra khỏi DG, về **thành gần bãi train
nhất**, leader **gôm party**, rồi cả đội chạy ra **điểm train**. Không có route farm riêng của DG —
xong DG là rơi thẳng vào flow Train chuẩn.

## Luồng (thứ tự bắt buộc)

1. Chốt account đang online; leader phải online.
2. Mỗi account đánh xong trận: dừng di chuyển DG, thoát DG, rời party cũ, phù về thành đã chọn.
   Không teleport trung gian random, không bán/cất đồ ở bước này.
3. Chờ **đủ** account được **server xác nhận** đã tới thành (không đoán theo đồng hồ).
4. Leader công bố phân khu live tại thành; member chuyển tới đúng phân khu đó.
5. Member mở nhận lời mời **trước** khi chờ leader. Leader mời và kiểm tra **đúng entity** từng
   member trong roster server (cùng map + cùng phân khu). Đủ đội -> chọn quân sư.
6. **Chỉ leader** chạy smart route/Ground path ra map train rồi tới tọa độ. Member theo party;
7. Không tự bật auto mà bây giờ luồng auto sẽ chuyển sang sài manual từ user ()
8. Xong: `ui_train_phase = "farming"`. Thất bại: giữ online, log lý do, KHÔNG chạy tiếp một mình,
   KHÔNG tự relogin chỉ vì không gặp quái.

Chi tiết từng bước + tên state: xem `references/flow.md`.

## Điểm vào trong code

| Việc | Chỗ code |
| --- | --- |
| Entry Android | `agent_bridge.start_farm_mode_json(mode, map_id, x, y, di_gioi_level)` |
| Bắt đầu team | `agent_bridge.auto_battle_team_json(map_id, x, y)` |
| Lệnh train (gôm/PT/route/combat) | `workflows/train.py::party_train_map(pidx, map_id, x, y)` |
| Handoff DG -> Train | `workflows/digioi.py::_android_dg_train_handoff(pidx, st)` |
| Thoát DG (đi bộ ra cổng 270,210) | `client.py::GameClient.exit_di_gioi()` |
| Đang ở DG? | `client.py::GameClient.in_di_gioi()` (`current_map == DIGIOI_MAP_ID`) |
| Thành gần bãi | `client.py::GameClient.nearest_smart_city(dest_map, exclude_map=dest_map)` |
| Về thành | `client.py::GameClient.go_to_town(city, flag)` |
| Mở nhận lời mời / mời / quân sư | `set_party_invite_ready(True)`, `invite_members()`, `set_party_strategist()` |
| Đi tới điểm train | `client.py::GameClient.navigate_to(x, y, ...)` / `follow_smart_route()` |

## Quy tắc khi sửa (rút từ docs/workflow-architecture.md)

- **KHÔNG gửi/nhận packet khi đang giữ `st["lock"]`** — xử lý invite có thể cập nhật roster đồng bộ.
- Sau mọi `wait`/hành động mạng, kiểm tra lại **session cancellation** và **`cmd_gen`** trước khi
  publish progress / mời / gửi lệnh mới.
- Feature mới -> **module riêng + entry point riêng**, không nhét nhánh mode vào workflow có sẵn.
- **Tái dùng** battle/heal config theo account đã lưu, KHÔNG ghi đè rule skill / ngưỡng HP/SP khi
  chuyển luồng.
- Chia sẻ primitive (protocol/kết nối/navigation), KHÔNG chia sẻ quyết định workflow.
- Không thêm fast-path "bỏ về thành" khi đã ở map train.

## Kiểm chứng

```bash
bash scripts/verify.sh
```

Chạy AST test thật của handler Train + handoff DG. Đây là kiểm thử logic, **không thay thế lượt test
online**. Khi kẹt, xuất log JSON trước Logout All; soi `ui_train_phase`, route plan, city-arrived,
party-invite-ready, roster count để biết bước nào chưa được server xác nhận.
