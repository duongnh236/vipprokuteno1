---
name: 40NPC
description: Dùng khi làm việc với event 40 NPC (đánh 40 trận liên tiếp, đổi quà chiến đấu) — khung giờ T2/T4/T6 20:00-22:00, vòng lặp leader, tránh ngắt kết nối mã 47, phục hồi giữa trận, đi đổi thưởng map 12003.
---

# 40NPC

Event **40 trận liên tiếp**, chỉ **leader** mở NPC và bấm đánh; cả party vào cùng trận do server
kéo. Chạy khung **Thứ 2 / Thứ 4 / Thứ 6, 20:00–22:00**. Sau event (sau 22h) đi **đổi quà chiến đấu**
ở NPC map 12003.

## Khung giờ & bật/tắt

- `npc40.in_event_window()`: `weekday() in (0, 2, 4) and 20 <= hour < 22`.
- `client.in_40npc_window()` bọc lại hàm trên.
- `npc40_force=True` (trong `PARTY_CONFIG` / `start_farm_mode_json`) = **bỏ qua khung giờ**, người
  dùng bấm nút muốn vào đánh ngay. Khi đó `run_loop(..., ignore_window=True)`.

## Vòng lặp (leader-only)

`client.start_npc40_loop(point, on_loss, before_repeat, ignore_window)` → thread `npc40-<label>`
chạy `npc40.run_loop(client, point, stop_event, on_loss, before_repeat, ...)`.

Các mốc chính trong `run_loop`:
1. `navigate_to(point)` (thử lại `MAX_THU_LAI=3` lần) → `_wait_combat_clear` → `sleep 3.0` cho
   **scene settle** → `rearm_ready()` (CHỈ 0x41, **không** `combat_ready()`).
2. `_open_event_battle`: `0x20 020008` → `0x14 0100 0500` → (advance nếu cần) → `0x14 0900 1e`
   (CHỌN CÓ) → `_advance_to_battle` (poll `_battle_start_seq`).
3. Chờ prompt trận kế: `_wait_counter(client, "_npc40_prompt_seq", ...)`.
4. Mỗi trận: hồi **FULL party** (`before_repeat` → `heal_npc40_between_battles`) rồi mở lại NPC.

Chi tiết + lý do từng mốc: `references/loop.md`.

## Quy tắc sống còn

- **KHÔNG gửi gói dialog/event khi tran đang chạy.** `S:000-000` mã **47**
  `<戰鬥未結束事件先結束>` → **đứt kết nối**. Mọi gói dialog phải qua `npc40._gui_dialog_an_toan`
  (chờ `_tran_dang_chay` = `state.in_battle` hoặc `_in_battle_end_grace`).
- 40 trận **liên tiếp**: khe giữa 2 trận rất hẹp → kiểm tra lại **trước TỪNG gói**, không chỉ 1 lần.
- Phân biệt page dialog **fresh** (`...4e`, cần advance) vs **giữa-event** (`...0200`/`...0300`,
  đã là choice). Advance thừa ở page choice → `0x14 08 01` → `0x00` **KICK**.
- Đi tới NPC rồi mở ngay (scene chưa settle) → server coi tương tác sớm → **KICK**.
- **KHÔNG** kết luận thua từ `alive=1/1`: `state.allies` chỉ mang unit chính leader. Dùng
  `npc40.party_song_that(client)` (đọc thẳng từng client cùng party). Bằng chứng thua thật =
  `_npc40_hp_snap` cho thấy quân nhà nằm hết (`_da_thua_that`).
- Mất kết nối / bấm Stop → `_wait_counter` trả `False` **không phải thua**; đừng báo party tan.

## Điều kiện kết thúc (`npc40._ket_thuc`)

| Lý do | Xử lý |
| --- | --- |
| Quá 22h (`past_window`) | Thoát; chưa tới 22h thì `_npc40_bo_thuong=True` (đổi thưởng sau, không mất gì) |
| Thua **2 trận liên tiếp** (`consec_loss >= 2`) | Thoát |
| `MAX_THU_LAI` lần liên tiếp không vào lại được trận | Thoát |

`_ket_thuc` gọi `on_loss()` (báo party ngừng + tan hàng), đóng dialog (`_end_npc_dialog`), set
`client._npc40_done = True`.

## Đổi thưởng

`client.claim_40npc_reward(ev)`:
- Đang ở map event `10991` → `exit_event` ra `12003`.
- Khác `12003` → `go_to_town(12001)` → `follow_smart_scene_route` tới `12003`.
- Trên `12003` → `navigate_to(NPC40_REWARD_NPC=(570,770))` → `0x20 020008` → `0x14 0100 0e00`
  (option `0x0e`) → `0x14 0600` ×4.

Điều phối leader phát lệnh đổi thưởng khi `c._npc40_done` (xem `run_party_digioi.py` ~7990).

## State / cờ

| Field | Ý nghĩa |
| --- | --- |
| `_npc40_prompt_seq` | tăng khi có prompt "đánh tiếp?" (cặp `0x41 0a0001` + dialog `...0300`) |
| `_battle_start_seq` | tăng mỗi `0x34` (vào trận) |
| `_npc40_hp_snap` | `(defeated, alive, total)` chốt HP cuối trận; reset mỗi trận mới |
| `_npc40_last_defeated` / `_last_alive` / `_last_total` | kết quả trận gần nhất |
| `_npc40_last_dialog` | hex page dialog gần nhất (fresh vs giữa-event) |
| `_npc40_bo_thuong` / `_npc40_done` / `_npc40_started` / `_npc40_stop` | trạng thái loop |

## Điểm vào code

| Việc | Chỗ code |
| --- | --- |
| Logic event + loop | `npc40.py` (`in_event_window`, `run_loop`, `_gui_dialog_an_toan`, `_ket_thuc`, `party_song_that`) |
| Bọc thread | `client.py::start_npc40_loop` / `stop_npc40_loop` |
| Quan sát packet | `client.py::_observe_npc40_packet`, `_chot_minh_chet` |
| Đổi thưởng | `client.py::claim_40npc_reward` |
| Hồi giữa trận | `run_party_digioi.py::_before_npc40_repeat` → `heal_npc40_between_battles` |
| Entry event | `agent_bridge.start_farm_mode_json` (mode `event`, `npc40_force`) |

## Kiểm chứng

```bash
python3 -B -m unittest discover -s tests -q -p 'test_android_safety.py'
```

Chú ý: `test_android_safety` hiện có 1 fail **có sẵn từ trước** ở
`test_navigation_never_counts_a_move_rejected_by_combat` (đang làm dở). Không liên quan 40NPC.
Test online bắt buộc cho event này vì phụ thuộc timing server.
