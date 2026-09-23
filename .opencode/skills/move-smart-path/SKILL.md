---
name: Move + Smart path
description: Dùng khi làm việc với di chuyển của ts_bot — lệnh move 0x06, dead-reckoning vị trí, chống ngắt kết nối "di chuyển quá xa" (mã 14), tìm đường trong map bằng Ground.mmg, tìm đường xuyên map bằng world_nav.json + smart_route, qua cổng và lên thuyền, và xử lý khi bị kéo sang map khác.
---

# Move + Smart path

Di chuyển có **3 tầng**, đừng lẫn:

1. **Lệnh move** — `move_to(x, y)` gửi `C2S 0x06`; server tự đi, **không echo** vị trí mình.
2. **Tìm đường trong 1 map** — `Ground.mmg` (`GroundMapStore.find_world_path`) qua `navigate_to`.
3. **Tìm đường xuyên map** — `world_nav.json` + cache `smart_routes.json` (`SmartWorldRouter`).

## Lệnh move (0x06)

`client.py::GameClient.move_to(x, y)`:
- Gói: `0x06  01 00 01 [x u16 LE][y u16 LE]`.
- **Không gửi khi đang trong trận** (`state.in_battle` hoặc `in_combat(idle_secs=1.0)`) và **không
  cộng `self.pos`** — giống client (`MoveController.lua:232`). Nếu vẫn cộng pos thì `pos` sai vĩnh
  viễn vì lệnh bị trận nuốt.
- **Dead-reckoning**: server không echo nước đi của mình, bot tự nhớ `self.pos = (x, y)`.

## Chống ngắt kết nối "di chuyển QUÁ XA" (mã 14)

Gửi **một** lệnh move tới điểm xa = `S:000-000` mã **14** `<移動距離過遠>` → **đứt kết nối**.
Vì vậy **mọi** đường đi đều phải chia đoạn:

| Hàm | Ngưỡng | Việc |
| --- | --- | --- |
| `navigate_to` | `config.SMART_PATH_SEGMENT` (100px) | chia từng waypoint thành các move-point |
| `_move_chia_doan` | `GameClient.ROUTE_BUOC_TOI_DA` (120) | cắt 1 chặng route dài thành nhiều lệnh move |
| `_route_move` | (gọi `_move_chia_doan`) | 1 bước route an toàn: chờ hết trận → move → nếu dính trận lại (lệnh bị nuốt) thì **move lại** |

Ngay cả khi **không có** Ground path, `navigate_to` vẫn chia đoạn (nếu biết `self.pos`) — thà đi sai
còn hơn làm rớt game.

## Tìm đường trong map (smart path)

- `_ground_store()` nạp `config.GROUND_MAP_PATH` (`gamedata/Ground.mmg`) khi
  `config.SMART_PATHFIND=True`. Không nạp được → rơi về `navigate_to` cũ (chia đoạn thủ công).
- `navigate_to(x, y, ..., require_smart_path=False)`:
  - **Sửa pos trước** khi tính đường: `_theo_leader_sua_pos()` (member đi theo leader) và
    `refresh_server_position()` nếu vừa bị kéo map / `pos is None`.
  - Nếu có Ground path: chia theo waypoint, `step = SMART_PATH_STEP_WAIT` (0.55s).
  - `require_smart_path=True` (SAFE NAV): **từ chối** nếu không có Ground path, hoặc đích nằm
    trong/vướng collision (Ground chỉ tới được điểm khác > 5px). Không fallback chia đường thẳng để
    tránh cắt qua collision.
  - **Đổi map giữa chừng** → **hủy** chuyến đi (đích thuộc map cũ, gửi move = mã 14).
  - Dính trận giữa đường → **dừng yên chờ**, không tính vào ngân sách bước (giống client), hết trận
    đi tiếp tới đúng đích; `_co_tran_giua_duong` đánh dấu lệnh move bị nuốt → **không** tự nhận "đã tới".
- `pathfind._blocked`: bit1 = chướng ngại, bit4 = chặn; **bit2 = biển KHÔNG phải chướng ngại**
  (đứng trên biển tự thành thuyền). Đừng thêm lại chế độ `boat=True` để tìm đường.

## Tìm đường xuyên map (smart world route)

- `_smart_world_router()` nạp `config.WORLD_NAV_PATH` (`world_nav.json`) + cache
  `config.SMART_ROUTE_CACHE_PATH` (`smart_routes.json`), khi `SMART_WORLD_ROUTING=True`.
- `SmartWorldRouter`:
  - `nearest_city(dest_map, exclude_city, allowed)` — thành gần **đi được** nhất (lọc cả thành chưa
    mở khi có `allowed`).
  - `build_route(dest_map, safe)` — tele thành + các leg qua cổng.
  - `build_scene_route(source_map, dest_map, safe, start)` — đi bộ nhiều map (dùng cho DG/event).
- `execute_smart_route(client, route, abort, flee)`:
  - Lên thuyền ở cổng vào scene biển đầu tiên; sail các leg biển; **không** rearm khi vừa lên
    thuyền/đang sail (0x41 làm rớt thuyền).
  - Cổng ra **map ngoài dự kiến** (cổng random nhiều đích / bị kéo lệch map) → **plan lại** đường
    còn lại từ map thực tế, tối đa `_MAX_ROUTE_REPLANS=16`, không bỏ cuộc.
  - `client._smart_route_failure` = `aborted` / `unexpected_scene` / `gate_failed`.
- `follow_smart_route(dest_map, safe)` = tele thành tốt nhất rồi đi cổng.
- `follow_smart_scene_route(source_map, dest_map, safe)` = đi bộ trong cùng thế giới map.

## Qua cổng & lên thuyền

`client.py::GameClient._enter_gate(x, y, idx, expected_map, board_boat, on_boat)`:
- Chỉ move tới cổng + gửi transit **khi hết trận**. Gửi khi đang battle → server nuốt lệnh hoặc ngắt.
- Chuỗi: `0x14 08[idx]` (qua cổng) → nếu cần `0x7c 04 00` (lên thuyền) → chờ map đổi → `scene_resume()`.
- **Cổng cho chọn** (`resultType==6`): trả lời bằng `0x14 09 + mã` (xem `GATE_CHOICE_CODES`), ghi nhớ
  mã đúng để lần sau dùng thẳng.
- `_gate_wait_clear`: chờ hết trận phục kích tại cổng, **tuyệt đối không gửi gì trong lúc chờ** (gửi
  `0x14 06` lúc server còn giải trận → server đóng kết nối).
- `scene_resume(settle)` = `0x0c 0100` + `0x14 0600` — bắt buộc sau khi đổi scene, không thì server
  nuốt lệnh move (đứng im).

## Vị trí thật & bị kéo map

- Server **không** echo move của mình → nguồn vị trí thật: `0x03` self-spawn / `S:012-000` /
  `S:007-000` / `S:013-004`, và **thấy acc khác cùng party di chuyển** (`S:006-001`).
- `_theo_leader_sua_pos()`: member trong party **tự đi theo leader** (client-side) → `self.pos` lệch
  dần. Chỉ bám **một lần** lúc vừa vào đội, không bám liên tục.
- Bị **kéo sang scene mới** (server đẩy, không tự qua cổng) → `_need_scene_resume` → chạy
  `scene_resume()` **trước** lệnh move đầu tiên rồi `refresh_server_position()`, nếu không → mã 14.
- `_pos_valid_for_map`: pos chỉ hợp lệ cho map đã đặt; qua cổng thì bỏ pos (trừ khi gói đổi map mang
  luôn toạ độ mới).

## Cấu hình liên quan

| Config | Ý nghĩa |
| --- | --- |
| `SMART_PATHFIND` | bật Ground.mmg |
| `SMART_WORLD_ROUTING` | bật world_nav + smart_route |
| `GROUND_MAP_PATH` / `WORLD_NAV_PATH` / `SMART_ROUTE_CACHE_PATH` | đường dẫn dữ liệu |
| `SMART_PATH_SEGMENT` (100) | px tối đa mỗi move-point |
| `SMART_PATH_STEP_WAIT` (0.55) | giây chờ mỗi bước smart path |
| `RUN_AROUND_OFFSETS` / `RUN_STEP_WAIT` / `RUN_RESUME_IDLE` | hình số 8 của AUTO TRUY KÍCH |

## Điểm vào code

| Việc | Chỗ code |
| --- | --- |
| Lệnh move | `client.py::GameClient.move_to` |
| Đi trong map | `client.py::GameClient.navigate_to` |
| Replay waypoint | `client.py::GameClient.follow_path` |
| Chia đoạn route | `client.py::GameClient._move_chia_doan`, `_route_move` |
| Qua cổng | `client.py::GameClient._enter_gate`, `scene_resume` |
| Route xuyên map | `client.py::follow_smart_route`, `follow_smart_scene_route`, `execute_smart_route` |
| Build route | `client.py::build_smart_route`, `build_smart_scene_route`, `nearest_smart_city` |
| Ground store | `pathfind.py::GroundMapStore`, `find_path`, `_blocked` |
| World nav | `world_nav.py::WorldNavStore` |
| Router + cache | `smart_route.py::SmartWorldRouter`, `SmartRouteCache` |

## Quy tắc khi sửa

- **Không bao giờ** gửi 1 lệnh move xa hơn ngưỡng (mã 14 → rớt kết nối → relogin dính mã 90 → cả
  party chờ dài).
- Không move khi đang trong trận; không gửi `0x14 06` khi server còn giải trận.
- Đổi map giữa chừng → **hủy** chuyến đi, không gửi move tới toạ độ của map cũ.
- Sau đổi scene phải `scene_resume()` rồi mới move.
- Đừng bịa toạ độ: không có `self.pos` thì xin lại từ server, không đoán.
- Lỗi tìm đường chỉ được phép "đi sai", **không** được làm rớt game.

## Kiểm chứng

```bash
python3 -B -m unittest discover -s tests -q -p 'test_city_exit.py'
python3 -B -m unittest discover -s tests -q -p 'test_android_safety.py'
```

Test liên quan: `test_dg_pursuit_requires_ground_and_generation`,
`test_pursuit_is_movement_only_and_stops_when_workflow_blocks_it`,
`test_navigation_never_counts_a_move_rejected_by_combat` (hiện **đang đỏ — WIP có sẵn**, chờ
`MOVE_XA_TOI_DA` / `self._move_chia_doan(x, y)`; không liên quan thay đổi mới).

Chi tiết route xuyên map (legs, thuyền, replan): `references/cross-map.md`.
