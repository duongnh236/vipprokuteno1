---
name: Dị Giới
description: Dùng khi làm việc với Dị Giới của ts_bot — vào/đổi cấp quái/thoát Dị Giới, đồng hồ 120 phút server cấp, mã trả lời S:097-001, Dị Giới Hộ Phù, pet solo nhiều con, truy kích trong DG, và pha DG trong luồng DG+Train.
---

# Dị Giới

Dị Giới là **map train chính** (`config.DIGIOI_MAP_ID = 49942`), có **giới hạn 120 phút/ngày**
(`DIGIOI_LIMIT = 120`) do **server** đếm. Vào/ra DG là việc của từng acc; luồng farm DG → train xem
skill `farm-di-gioi`.

## Vào Dị Giới

`client.py::GameClient.enter_di_gioi()`:
1. **Phải rời tổ đội trước** (`leave_party`). Client chặn vào DG khi còn đội (`Team.IsAlone`); gửi
   khi còn đội → server trả `S:097-001` mã **5** `<組隊中>`.
2. `0x61 010001` (mở/load zone DG) → chờ 1.5s.
3. `0x61 02 00 [idx]` (xác nhận vào + chọn cấp quái).
4. Spawn DG cố định → set `pos = RUN_FALLBACK_ANCHOR (870,740)` và chốt `_di_gioi_anchor` (tâm
   run-around, tránh rìa map sau relogin).

**Nên dùng `enter_di_gioi_safe(tries=12, wait=3.0)`** thay vì gọi thẳng: nó **chờ `S:097-001`** rồi
mới xử lý, không bắn lại mù. Chi tiết mã + vì sao: `references/enter-codes.md`.

## Đổi cấp quái (live)

- `DI_GIOI_LEVELS = [10,25,40,55,70,85,100,110,120,130,140,150,160,170,180]`, `idx = 1..15`.
- `set_di_gioi_level(idx)` gửi `0x61 02 00 [idx]` — **đổi được ngay khi đang ở trong DG**, không cần
  vào lại. Mặc định `di_gioi_level = 2` (cấp 25).
- Tự chọn cấp theo level party: `di_gioi_pick` → điều phối chốt 1 lần cho cả party
  (`_doc_cap_dg`), tránh mỗi acc ra một mốc.

## Đồng hồ 120 phút

- `client.digioi_minutes` = số phút **đã dùng**, đọc từ RoleCount `0x1b` (gói `0x55`).
- `client.digioi_minutes_live()` = số phút đã dùng **ngoại suy tới lúc gọi** (chỉ cộng khi đang ở
  trong DG). Server ngừng đẩy gói → số đóng băng, nên **phải** dùng hàm live, không đọc số thô.
- `run_party_digioi.py::_acc_het_gio_dg(c)` → `True` hết · `False` còn · `None` **chưa biết**:
  - `S:097-001` mã 2 → hết;
  - chưa có đồng hồ (`_last_digioi_ts == 0`, vd vừa login lại) → `None` (phải chờ, không kết luận);
  - còn lại `(DIGIOI_LIMIT - digioi_minutes_live()) < 1`.
- `_het_gio_dg(c)` (bản cũ hơn) còn tính "ra ngoài map DG mà còn < 2 phút" = hết giờ thật.

## Thoát Dị Giới

`client.py::GameClient.exit_di_gioi()`:
- DG **không có lệnh thoát** — phải **đi bộ tới cổng `DIGIOI_CONG_RA = (270, 210)`**, tới cổng map
  tự đổi.
- `flee_mode = True` suốt đường ra (né trận, không dừng đánh), ưu tiên smart path `navigate_to`,
  fallback chuỗi bước capture.
- Gửi `0x14 08000100` → `0x0c 0100` → `0x14 0600`; xác nhận bằng `_left_di_gioi()` (đọc
  `current_map`, **không** dựa số kênh).
- **Không bỏ cuộc**: kẹt trong DG là kẹt vĩnh viễn. Chỉ dừng khi đã ra / acc STOP / rớt mạng.
- `go_to_town()` **tự gọi `exit_di_gioi()` trước** mọi thứ (kể cả khi thành chưa mở) — ra khỏi DG là
  việc bắt buộc.

## Tính năng trong DG

| Việc | Chỗ code |
| --- | --- |
| Đang ở DG? | `client.py::in_di_gioi()` (`current_map == DIGIOI_MAP_ID`) |
| Mua Hộ Phù | `client.py::buy_di_gioi_ho_phu` |
| Dùng Hộ Phù | `client.py::use_di_gioi_ho_phu` |
| Pet solo nhiều con | `state.solo_multipet` (DG solo tối đa 4 pet **cùng lượt**, atype 0/1/3/4; `combat.decide_multipet`) |
| Truy kích DG | AUTO TRUY KÍCH (skill `auto-battle-pursuit`, manual); `_dg_pursuit_paused` |
| Tâm run-around | `_di_gioi_anchor` (điểm tele vào, cố định) |

## Đánh trong DG — KHÔNG tự động

Dị Giới **không** tự bật engine đánh. Việc đánh do công tắc **AUTO BATTLE** của user quyết định —
chi tiết ở skill `auto-battle-pursuit` (manual, chỉ user gọi; xem mục AUTO BATTLE).

- `combat_ready()` chỉ là **re-arm** (gửi lại chuỗi setup) và **thoát ngay (no-op) nếu
  `_auto_battle_enabled` đang tắt**. DG không gọi nó để bật đánh.
- `_auto_battle_enabled = True` **chỉ** được set trong `apply_auto_mode` (`client.py`), gọi từ
  `agent_bridge.set_auto_mode_json` (nút bấm của user) hoặc restore từ setting đã lưu.
- Truy kích DG (`_dg_pursuit_paused` / run-around) cũng chỉ chạy khi user bật **AUTO TRUY KÍCH**.

→ **Chưa bật AUTO BATTLE thì acc ở DG đứng yên, không tự đánh.**

## Cấu hình / entry

- `PARTY_CONFIG.mode`: `digioi` (chỉ DG), `digioi_train` (DG trước, xong → train).
- `START_CITY_ID == DIGIOI_MAP_ID` → train DG (run-around).
- `di_gioi_level` (idx 1..15), `di_gioi_pick`.
- `agent_bridge.start_farm_mode_json('digioi'|'digioi_train', map_id, x, y, di_gioi_level)`.
- `use_digioi_ho_phu` (bật/tắt dùng Hộ Phù).

## Quy tắc

- Vào DG **phải** rời đội trước.
- **Không** kết luận "hết giờ" khi chưa có đồng hồ server (`None` ≠ hết).
- **Không** bỏ cuộc khi chưa ra khỏi cổng DG.
- Đổi cấp quái thì đổi **live**, đừng bắt acc ra vào lại.
- Relogin làm mất mốc đồng hồ → `relogin()` bỏ `_last_digioi_ts`, chờ server đẩy lại.

## Kiểm chứng

```bash
python3 -B -m unittest discover -s tests -q -p 'test_android_safety.py'
```

Test liên quan (đều nằm trong `test_android_safety.py`): `test_dg_pursuit_requires_ground_and_generation`,
`test_dg_handoff_waits_for_all_command_loops_and_dispatches_once`,
`test_dg_snapshot_excludes_offline_configured_accounts`,
`test_map_train_clears_all_dg_runtime_flags`.
