---
name: Rương đồ
description: Dùng khi làm việc với tab RƯƠNG ĐỒ của ts_bot — xem/khóa/vứt/dùng/hợp/trang bị/phân giải vật phẩm, mở rộng túi/tiền trang, cache túi, dọn túi tự động, và hàng đợi lệnh khi đang trong trận.
---

# Rương đồ

Xem và thao tác vật phẩm trong túi. Server gửi snapshot túi; bot lưu cache để xem lại khi acc tắt.

## Điểm vào

| Việc | Chỗ code |
| --- | --- |
| Render tab (sectionMode=1) | `AccountManagerView.java::renderBag` |
| Dựng JSON túi | `run_party_digioi.py::bag_info` + `_bag_info_slots` (khóa `slots/live/ts/cap/used/maxed`) |
| Luật nút DÙNG/DEO/PHÂN GIẢI/HỢP | `train_bot/bag_tabs.py`: `can_use`, `can_dismantle`, `can_equip`, `matches_tab`, `category_of` |
| Cầu hành động UI→Python | `agent_bridge.py::account_action_json` → `client.py` |
| Túi 1 acc (nhẹ, cho UI) | `agent_bridge.py::bag_json(username)` → `run_party_digioi.py::bag_info` |
| Snapshot túi | S2C `0x17 sub=0500` (THAY THẾ toàn bộ) + `0x17 sub=0800` (1 ô); record 36B `[idx][item_id u16][count u32][pad]`, `idx` = use-id |

## Hành động (qua `account_action_json`)

| action | `client.py` | Opcode |
| --- | --- | --- |
| `use_item` | `use_slot` | `0x17 0f00 [slot][qty] 000000 [target] 00` |
| `equip` | `equip_item` / `equip_pet_item` | `0x17 0b00 [slot]` / `0x17 1100 [petIdx][slot]` |
| `decompose` | `decompose_slot` | `0x59 03 00 01 [slot][01] 000000` |
| `discard` | `discard_item` | `0x17 0300 [slot][qty LE32]` |
| `combine` | `combine_slots` / `do_combine_item` | `0x17 0e00 [cid1 u16]...[cid2 u16]... 01`, `cid=0x100+slot` |
| `toggle_lock` | `set_item_lock` / `item_locked` | **không gửi packet** — khóa phía bot |

## Dùng nhanh + cập nhật số lượng (APK)

- Lệnh túi chạy trên **executor riêng** (`MainActivity.actionIo`), KHÔNG xếp sau 3 poll
  dashboard/status/daily → hết cảnh "dùng vật phẩm rất chậm".
- `use_item` gọi `client.use_slot_wait()` (thay vì `use_slot`): gửi lệnh rồi **chờ ack `0x17/0900`**
  (ack này tự trừ `bag_slots[slot][1]`) và trả `count` mới → UI cập nhật số ngay, không đợi poll 2.5s.
- Sau mỗi lệnh túi, APK gọi bridge nhẹ `bag_json(user)` (không quét cả 5 acc) rồi
  `AccountManagerView.updateBagLive()` cập nhật **tại chỗ** (số lượng, cờ khóa, nút); chỉ dựng lại
  khi **danh sách ô đổi** (mất/thêm ô, vd dùng hết item).
- Ô đang chờ server hiện **spinner nhỏ** (`progressBarStyleSmall`) và bị khóa nút
  (`bagPendingSlots`) để không bấm trùng; dashboard poll **không** mở lại nút khi còn chờ.
- **Cuộn**: `AccountManagerView.renderBody()` giữ `bodyScroll.getScrollY()` rồi khôi phục sau khi
  dựng lại (trước đây rebuild làm tuột lên đầu / nhảy xuống cuối). Tab RƯƠNG ĐỒ **không rebuild**
  mỗi poll 2.5s nữa (chỉ cập nhật tại chỗ).

## Dung lượng & mở rộng

- `bag_capacity() = 50 + sum(RoleCount 103,106,124)*5`; `bag_used_slots`, `bag_free_slots`, `bag_first_empty_slot`.
- Mua ô túi: `query_bag_slot_price`/`buy_bag_slot` (`0x54 sub01/02 sellId=3`); tiền trang: sellId=1.
- `tu_mo_rong_tui` — hiện **KHÔNG gọi khi login** (đã comment, xem skill `login` #10).

## Cache & dọn túi

- Cache: `_ghi_cache_tui`→`save_bag_cache`/`load_bag_cache`; kho: `_ghi_cache_kho`/`save_bank_cache`.
  Cache là **CHỈ XEM** — UI phải khóa nút khi `live=False`.
- Tự dọn: `discard_junk_items` (`DISCARD_JUNK_TIDS={0x59f0}`), `decompose_junk_scrolls`,
  `deposit_fashion_to_collection`, `sell_noi_dat` (`NOI_DAT_TID=0x7D2B`, `0x1b 0200 01 [slot][qty LE16] 0000`).
- Trong trận: `account_action_json` **chặn** nhiều action ("Đang trong trận..."); lệnh tay xếp hàng
  `queue_bag_cmd` → `_flush_bag_queue`/`_bag_flush_worker`.

## Quy tắc / gotcha

- `bag_tabs.can_use`: `bs > 0` = **KHÔNG** dùng được (ngược trực giác).
- Vật phẩm **khóa**: không vứt, không dùng, không hợp; **không** mở khóa được khóa gốc của game.
- `combine`: 2 slot hợp lệ; cùng slot cần `cnt>=2`; `restrict & 4` không hợp được.
- Túi đầy → **không cởi đồ được**; mở thẻ phải kiểm `GetBagLeftCount`.
- Server **không** gửi `0x16` refresh sau khi vứt; `0x17 sub05` là ghi đè toàn bộ.
- `decompose` là **mất hẳn** — mặc định `auto_decompose_scrolls=False`.

## File dữ liệu

`items_gamedata.json` (`_load_gamedata_items`), `use_items.json`, `junk_scrolls.json`,
`donate_items.json`, `collect_style.json`, `pet_scrolls.json`.
