---
name: Bản đồ
description: Dùng khi làm việc với tab BẢN ĐỒ của ts_bot — vẽ bản đồ + toạ độ live của party/entity, tap bản đồ để leader kéo team, snapshot bản đồ, collision Ground.mmg, và quét bãi quái.
---

# Bản đồ

`TeamMapView` vẽ terrain + team/entity live; tap bản đồ = **leader kéo nguyên party** tới toạ độ.

## Kiến trúc vẽ (2 lớp — chống lag)

`TeamMapView` chia **2 lớp** để cập nhật toạ độ mượt:

| Lớp | Nội dung | Khi nào vẽ lại |
| --- | --- | --- |
| **TĨNH** (`staticBmp`) | nền + lưới + địa hình + SAFE + đích + tiêu đề/chú thích | **1 lần** khi vào map / đổi vùng nhìn / đổi kích thước / có địa hình mới (`drawStatic`, key `staticKey`) |
| **ĐỘNG** | người chơi / quái / member / route / dấu chạm / bộ đếm | mỗi frame, **đã cull ngoài khung** |

- Vị trí động được **nội suy** (`updateAnimTargets` + `postOnAnimation`, `ANIM_MS=900`) giữa 2 snapshot
  (poll 1 giây) → di chuyển mượt thay vì nhảy cục. Chỉ chạy vòng lặp vẽ lại khi **có thay đổi thật**
  (đứng yên thì dừng → đỡ tốn pin).
- Camera **chốt 1 lần** khi vào map; chỉ recenter khi điểm neo tới gần biên (`>640` khỏi tâm) → hạn chế
  vẽ lại lớp tĩnh.
- **Full-screen**: màn BẢN ĐỒ trong `AccountManagerView` ẩn `titleView` + `bodyScroll`, hiện `mapHost`
  (`TeamMapView` chiếm hết khung, nút "← THÔNG TIN" nổi góc trên-trái). Màn map ở `MainActivity`
  (`teamMapView` trong `pageHost`) vốn đã full-screen.

## Điểm vào

| Việc | Chỗ code |
| --- | --- |
| Vẽ map, team/entity/safe/target/route | `TeamMapView.java::onDraw`, `drawStatic`, `renderTerrain`, `blocked` |
| Nhận snapshot + decode collision base64 | `TeamMapView.java::setSnapshot`, `setRoute` |
| Tap map → callback | `TeamMapView.java::onTouchEvent` → `OnMapTapListener` |
| Gắn listener | `MainActivity.java::buildTabbedUi` (`moveTeamFromMap`); `AccountManagerView.java::renderAccountMap` (sectionMode=5) |
| Poll 1s | `MainActivity.java::mapPoll` / `refreshMapSnapshot` → `agent_bridge.py::map_snapshot_json` |
| Bridge snapshot | `agent_bridge.py::map_snapshot_json` (collision cache `_ground_ui_cache`) |
| Bridge tap di chuyển | `agent_bridge.py::move_team_json` → `run_party_digioi.py::party_move_to` → cmd `"point"` |
| Đọc Ground collision | `client.py::_ground_store`; `pathfind.py::GroundMapStore` (get/world_to_block/nearest_walkable_world/find_world_path) |
| Quét bãi quái | `train_bot/mob_scanner.py::scan_full_map`/`MobScanSession`; cache `mob_spots.py` |

## JSON keys

- `map_snapshot_json(username, with_collision)` trả: `ok, map, map_name, focus_user, channel, team[], entities[], target, safe[], collision`.
  - `team[]`: `user, name, map, channel, x, y, position_source, leader, in_party, strategist, int`.
  - `entities[]`: `id, template_id, name, kind ("player"/"mob"), x, y` (tối đa 250).
  - `collision`: `grid_w, grid_h, origin_x, origin_y, cell(=20), data(base64)`.
- `move_team_json(x, y)` trả: `ok, message, requested, target, path[]`.

## State

`pos`, `current_map`, `_position_generation`, `self_entity`, `world_entities`(+lock), `entity_names`,
`entity_meta`, `party_members/party_leader`, `st["mob_spot"]`, `GroundMapStore.index/data`.

## Quy tắc / gotcha

- **Chỉ leader di**: `move_team_json`/`party_move_to`/cmd `"point"` — member **tuyệt đối không** tự navigate.
- Team **lệch map/kênh** → từ chối lệnh tap.
- **Không bịa toạ độ**: snap về ô đi được gần nhất (`nearest_walkable_world`); không có path → lỗi;
  toạ độ ngoài `0<x<20000` bị chặn.
- Toạ độ entity server broadcast có thể **mới hơn** `pos`, nhưng **chỉ để VẼ UI** — **không** ghi đè
  toạ độ dùng cho navigate/combat. `position_source` = `account` hoặc `server_entity`.
- `map_snapshots_json` (bridge) định nghĩa nhưng **không có caller** Java.

## Kiểm chứng

```bash
python3 -B -m unittest discover -s tests -q -p 'test_android_safety.py'
```
Test: `test_navigation_never_counts_a_move_rejected_by_combat`, `test_dg_pursuit_requires_ground_and_generation`,
`test_team_json_is_bounded_and_omits_credentials`.

Dữ liệu: `gamedata/Ground.mmg`, `world_nav.json`, `map_gates.json`, `train_maps.json`;
`mob_spots.json` sinh lúc chạy (không có trong repo).
