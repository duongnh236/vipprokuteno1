# Route xuyên map — chi tiết

Nguồn: `smart_route.py`, `world_nav.py`, `client.py::execute_smart_route`.

## Dữ liệu

- `world_nav.json` (`WorldNavStore`): `edges` (đồ thị có hướng `from -> to`), `gates` (toạ độ tâm
  cổng theo `scene`/`door`), `cities`, `fingerprint`.
  - `find_scene_routes(source, target)`: BFS ngược từ target → mọi đường, sắp theo (số leg, edge key).
  - `rank_cities(target)`: thành xếp theo `gate_count` rồi `city`.
  - Cổng có `image == [0,0,0]` = **warp event/script**, đi bộ tới + `0x14 08` **không** đổi map →
    xếp sau cổng thật (`_gate_unusable`).
- `smart_routes.json` (`SmartRouteCache`): cache route theo `(dest_map, safe)` + `fingerprint`.
  Fingerprint = `nav.fingerprint : _ROUTE_CACHE_VERSION`. Đổi dữ liệu → bump version để bỏ cache cũ.
  Ghi bằng file tạm + `os.replace` (atomic).

## Cấu trúc route

```
{
  "dest_map", "safe", "city", "flag", "arrival", "total_distance",
  "legs": [ { "scene", "target_scene", "from_code", "to_code",
              "gate", "gate_center", "paths": {start_key: [points]},
              "target_arrival" } ],
  "final_paths": {start_key: [points]}
}
```
- `paths` cache đường bộ trong 1 scene theo `_start_key(start)` = `ceil(x/20),ceil(y/20)`.
- `target_arrival` = điểm rơi sau cổng. Khi map **vòng một chiều** không có cổng ngược →
  `_arrival_after` trả None; build lấy **tâm cổng kế tiếp** (ô đi được gần đó) làm điểm rơi, cuối
  cùng fallback `SceneFight` seed. Điểm rơi lúc BUILD chỉ để validate/ước lượng; **runtime
  `navigate_to` pathfind từ pos THẬT** nên không sai.
- `_ONE_WAY_TARGET_ARRIVALS`: bảng cổng một chiều không suy được điểm rơi (vd `11011->11000`,
  `13422->13423`) — thêm cổng mới loại này thì bổ sung ở đây.

## Thực thi (`execute_smart_route`)

1. `_route_boat_state(route)`: leg nào ở nước (`is_sea_world` tại `gate_center`) → cần thuyền.
   `board_leg = first_sea - 1` (bến trước scene biển đầu).
2. Duyệt từng leg:
   - `current_map != leg.scene` → `_smart_route_failure = "unexpected_scene"`, dừng.
   - `navigate_to(gate_center, ...)` tới cổng (chờ hết trận trên đường).
   - `_in_scene_gate = True` quanh `_enter_gate` (mỗi acc đánh trận phục kích cổng riêng).
   - `_enter_gate(..., expected_map=leg.target_scene, board_boat=..., on_boat=sailing)`.
   - Cổng ra **map khác** `target_scene`:
     - nếu đã tới `dest_map` → xong;
     - chờ có toạ độ mới (`0x03`), `build_smart_scene_route` từ map thực tế → **plan lại**; tối đa
       `_MAX_ROUTE_REPLANS=16`; hết → `unexpected_scene`.
   - Không phải leg thuyền → `rearm_ready()` (0x41) để leg sau move được.
3. Tới `dest_map`, nếu có `safe` → `navigate_to(safe)`.

## Cổng & chọn mã

- `_enter_gate` gửi `0x14 08[idx]`; cổng có cutscene/choice thì server trả `resultType==6` →
  `_send_gate_choice` trả `0x14 09 + mã` (`GATE_CHOICE_CODES`). Mã đúng được nhớ trong
  `_GATE_CHOICE_STATE` theo `(map, idx)` để lần sau dùng thẳng.
- `board_boat=True` → thêm `0x7c 04 00` sau `0x14 08` (server ghi nhận "trên thuyền"); **không** gửi
  `0x41` khi vừa lên thuyền/đang sail (0x41 làm rớt thuyền).
- `_gate_wait_clear`: chờ hết trận phục kích, **không gửi gì trong lúc chờ**.

## Bị kéo map / đổi map giữa chừng

- `navigate_to` chụp `_map_bat_dau`; nếu `current_map` đổi → hủy chuyến đi (đích thuộc map cũ).
- `_enter_gate` sau khi map đổi: giữ `pos` nếu gói đổi map mang toạ độ mới (`_pos_valid_for_map == cm`),
  ngược lại `pos = None`; rồi `scene_resume()`.
- `_need_scene_resume` (bị kéo không tự qua cổng): `navigate_to` chạy `scene_resume()` +
  `refresh_server_position()` trước lệnh move đầu.

## Liên quan skill khác

- AUTO TRUY KÍCH (`auto-battle-pursuit`, manual) dùng `navigate_to(require_smart_path=True)` theo
  `RUN_AROUND_OFFSETS` và bám ô đi được (`_bam_o_di_duoc`) — không bịa toạ độ.
- Train/DG dùng `follow_smart_route` / `follow_smart_scene_route` để ra bãi và về thành.
