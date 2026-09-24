---
name: Dịch chuyển
description: Dùng khi làm việc với tab DỊCH CHUYỂN của ts_bot — teleport về thành, thành đã mở (warp/mark), tele cả party, thoát/vào Dị Giới, thoát map event, và các trường hợp teleport bị chặn (đang trận/DG/PB/instance).
---

# Dịch chuyển

Về thành qua lệnh teleport `0x44`; một số ngữ cảnh **không teleport được** → phải thoát ra trước.

## Điểm vào

| Việc | Chỗ code |
| --- | --- |
| Teleport thô (`0x44 01 00 [city u16][flag u8]`), phải rời tổ đội trước | `client.py::teleport` |
| Về thành lặp tới khi map đổi | `client.py::go_to_town` |
| Thành đã mở? (True/False/**None**) | `client.py::city_unlocked` (dựa `warp_points.json` + `mark_bitids.json` + mark_flags) |
| Thoát Dị Giới (đi bộ tới cổng `(270,210)`) | `client.py::exit_di_gioi` |
| Vào Dị Giới | `client.py::enter_di_gioi` / `enter_di_gioi_safe` |
| Đang trong map event (tháp 2K) → đi bộ ra | `client.py::_di_bo_ra_khoi_map_event` / `exit_event` |
| Sau đổi scene | `client.py::scene_resume` (`0x0c 0100` + `0x14 0600`) |
| Bridge tele 1 acc | `agent_bridge.py::teleport_city_one_json` |
| Coordinator tele cả party | `run_party_digioi.py::party_teleport_city` (cmd `("city", id, flag)`) |
| Chọn thành xuất phát cả party đều mở | `run_party_digioi.py::_pick_start_city`, `_party_unlocked_cities` |
| UI tab "THÀNH ACCOUNT ĐÃ MỞ" | `AccountManagerView.java::renderTeleport`; nút `MainActivity.java::teleportOne` |

## Luồng UI → bridge

- Dashboard trả `cities_loaded` + `cities[]` = **chỉ thành `city_unlocked(...) is True`**.
- `teleport_city_one_json(username, city_id)`: lỗi nếu không có trong `TELEPORT_CITIES`;
  `None` → "Server chưa trả danh sách thành đã mở"; `!= True` → "Account chưa mở thành này".

## Quy tắc / gotcha

- **Thành chưa mở → bỏ ngay, không spam.** `None` = **chưa biết**, KHÔNG được coi là `False`.
- **Đang trong trận** → không tele; chờ hết battle (`state.in_battle`).
- **Đang Dị Giới / PB / instance** → tele bị chặn: phải `exit_di_gioi()` / `leave_team_dungeon()`
  (`C:047-010`) / `leave_single_dungeon()` (`C:013-004`) trước. **Map event** → đi bộ ra bằng `exit_event`
  (đang leo tháp thì KHÔNG tự ra).
- **Phải rời tổ đội trước** khi tele/đổi kênh (`Team.IsAlone`).
- **Chuỗi `0x14 06` khi còn trận** → `S:000-000` mã **47** → đứt kết nối. Tele do bot ra lệnh **không**
  gửi `0x14 06`; nhưng bị server kéo map thì phải `scene_resume()` rồi mới move (không thì mã 14).
- Đổi map → **danh sách kênh cũ hết giá trị**.
- Mode CITY thành chưa mở: **không** đi bộ lẻ từng acc (cổng có hội thoại 1 người trả lời) → dùng
  lệnh "DI MAP" cho cả party.

## Kiểm chứng

```bash
python3 -B -m unittest discover -s tests -q -p 'test_city_exit.py'
python3 -B -m unittest discover -s tests -q -p 'test_android_safety.py'
```

Dữ liệu: `cities.json` (note opcode `0x44`), `warp_points.json`, `mark_bitids.json`, `map_gates.json`.
