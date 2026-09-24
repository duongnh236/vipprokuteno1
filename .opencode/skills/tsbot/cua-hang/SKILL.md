---
name: Cửa hàng
description: Dùng khi làm việc với tab CỬA HÀNG / LÒ của ts_bot — mua Dị Giới Hộ Phù, Túi Triệu Gọi, Hộp Thiên Châu, mua HP/SP ở Trác Quận, mở rộng túi/tiền trang, rút thẻ (gacha), lò thường/hoàng kim, và đổi quà sự kiện.
---

# Cửa hàng

Mua vật phẩm bằng xu/tiền đồng. Nhiều mục **đếm lượt từ server** (RoleCount `0x55`) nên bot không
mua quá giới hạn.

## Điểm vào

| Việc | Chỗ code |
| --- | --- |
| Cầu hành động UI→Python | `agent_bridge.py::account_action_json` (allowlist) |
| Render tab (sectionMode=6) | `AccountManagerView.java::renderShop` / `shopCard` |
| Tab lò (sectionMode=7) | `AccountManagerView.java::renderFurnace` |
| JSON shop/lò cho UI | `agent_bridge.py::accounts_dashboard_json` (`bag`, `furnace`, `shop`) |

## Hành động / giá / opcode

| Mục | `client.py` | Ghi chú |
| --- | --- | --- |
| Dị Giới Hộ Phù | `buy_di_gioi_ho_phu` | `0x42`, item `0xff8c`, giá **36**, counter `0x55 sid=0x0456` |
| Túi Triệu Gọi | `buy_trieu_goi_bao_hop` | item `0xb554`, giá **60000**, slot 7; cần `xu > ngưỡng` |
| Hộp Thiên Châu | `buy_hop_thien_chau` | item `0xb68a`, giá **39**, slot 6; **chỉ login** (không có trong `account_action_json`) |
| Mua HP/SP | `buy_hp_sp` | ở Trác Quận 12001, giá **20**, slot HP=1/SP=2; **chỉ login/giữa phiên** |
| Rút thẻ pet | `claim_gacha_pet` | `0x42` + 3×`0x5b`; `GACHA_COST=9000` |
| Rút thẻ tướng | `claim_gacha_card` | như trên |
| Soi lò | `scan_furnace` | `0x59 0100` → `_parse_furnace_shop` |
| Mua lò | `buy_furnace_item` | `0x59 0200 [kind][slot][itemId u16]`; kết quả `1=OK,5=đã mua,6=thiếu chips` |
| Xử lý lò theo config | `process_furnace` | `_mua_luot` chặn mua trùng; giá hoàng kim **×2** |

- Lò: thường `{vo_tuong:1, trang_bi:2, chuyen_sinh:5}`, hoàng kim `{3,4,6}`.
- Đổi quà sự kiện: `do_event_exchange` (`0x7c 0300 [missionId u32][times u32]`), kế hoạch `event_exchange.py::plan_for`.
- UI đọc counter: `shop.ho_phu_used/ho_phu_max`, `bao_hop_used/bao_hop_max`, `gacha_pet_remaining`, `gacha_card_remaining`.

## Quy tắc / gotcha

- **Phải ĐÓNG dialog shop trước khi tele** (`finally` gửi `0x14 0600` rồi mới về thành) — đang mở
  shop/thoái mà teleport là **chết**.
- Gacha cần `xu >= 9000`; server **không** push lại balance → bot tự trừ `self.xu`.
- Counter lấy từ `0x55`; đã đủ max thì bỏ qua.
- Trong trận: `account_action_json` chặn `buy_*`, `gacha_*`, `furnace_buy`.
- Lò chỉ ack `S:089-002` (không có `0x17 sub08`) → dùng `_mua_luot` chặn mua trùng giữa 2 lò.
- Lò hoàng kim chưa mở → server trả 8 slot `id=0`.

## File dữ liệu

`items_gamedata.json`, `furnace_pool.json`, `furnace_default_notify.json`, `exchange.json`,
`use_items.json`. Cache runtime: `event_exchange.json` + `event_exchange_sig.txt`.
