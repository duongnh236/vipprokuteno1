# 40NPC — chi tiết vòng lặp

Nguồn: `npc40.py`. File này giải thích **vì sao** từng mốc, để sửa không phá timing.

## Hằng số

| Tên | Giá trị | Ý nghĩa |
| --- | --- | --- |
| `CHO_TRAN_XONG_SEC` | 8.0 | chờ server giải xong trận trước khi gửi dialog/event |
| `CHECK_CHO_PROMPT` | 450 | số lần poll chờ prompt (× `poll_interval=0.4s` = 180s) |
| `MAX_THU_LAI` | 3 | số lần thử mở lại NPC / vào lại trận trước khi bỏ |

## Vì sao không gửi dialog giữa trận

Gửi gói dialog/event khi server còn trong trận → `S:000-000` mã **47**
`<戰鬥未結束事件先結束>` → **đứt kết nối**. 40NPC là các trận nối tiếp nên khe giữa hai trận hẹp;
gửi 3 gói cách nhau 0.5s là gần như chắc chắn có lần rơi vào trận.

→ Mọi gói dialog đi qua `_gui_dialog_an_toan`: chờ `_tran_dang_chay(client)` (=
`state.in_battle` HOẶC `_in_battle_end_grace`) hết, tối đa `CHO_TRAN_XONG_SEC`; nếu vẫn đang chạy
thì **bỏ gói** (trả `False`), không gửi.

## Vì sao phải "rearm nhẹ"

Trước khi mở NPC, code gọi `client.rearm_ready()` (chỉ `0x41`), **không** `combat_ready()`.
`combat_ready` gửi cả chuỗi `_login_setup` (0x57/0x01/0x62/0x7c…) ngay trước khi mở NPC event →
server loạn state lúc trận spawn → `0x14 08 01` → `0x00` KICK. Người chơi thật không gửi chuỗi
login trước NPC.

## Phân biệt page dialog

`_open_event_battle` mở `OPEN_NPC = 0x14 0100 0500`, rồi đọc `_npc40_last_dialog` (hex của
`0x14 sub0100`):

- **FRESH** (đầu event): page1 chưa có choice, hex kết thúc bằng counter `...4e` → cần **1 advance**
  (`0x14 0600`) để ra page2-choice.
- **GIỮA-EVENT** (đang dở 40 trận): prompt "đánh tiếp?" kết thúc `...0200` hoặc `...0300` = **đã là
  choice** → chọn LUÔN, **không** advance.

Advance thừa khi page đã là choice → `0x14 08 01` → `0x00` KICK. Vì vậy chỉ advance khi
`not (dialog.endswith("0200") or dialog.endswith("0300"))`.

## `_advance_to_battle`

Sau `CHOOSE_YES = 0x14 0900 1e`, gửi `ADVANCE` và **poll sát 0.1s** để dừng ngay khi trận bắt đầu:

- `_battle_start_seq` tăng ở `0x34`; `state.in_battle` tăng sớm hơn ở `0x35` (lượt đầu).
- Chỉ nhìn `_battle_start_seq` sẽ có khe hẹp gửi lố 1 `ADVANCE` vào trận vừa spawn → `0x14 08 03`
  → `0x00` KICK. Vì vậy kiểm cả `_tran_dang_chay(client)`.

## Vòng chờ prompt & kết luận thua

`_wait_counter(client, "_npc40_prompt_seq", ...)` trả `False` ở hai tình huống **khác hẳn nhau**:

- **hết số lần chờ** → thật sự không có prompt → (có thể) thua;
- **`not _active()`** (acc rớt / bấm Stop) → **KHÔNG phải thua**, trả về để supervisor relogin.

Nếu hết chờ: chỉ kết luận **thua** khi `_da_thua_that(client)` (chốt HP cho thấy quân nhà nằm hết).
Không có bằng chứng → coi là trục trặc, `thu_lai += 1`, đóng dialog rồi mở lại NPC; quá
`MAX_THU_LAI` mới bỏ cuộc. (Trước đây `return False` câm → `on_loss()` không chạy → cả party đứng
chết.)

## Hồi phục giữa trận

Sau mỗi trận: **đóng dialog trước** (`_end_npc_dialog` = CHỌN KHÔNG + 2 advance), rồi mới
`before_repeat()` → `heal_npc40_between_battles()`. Dùng item lúc prompt còn mở → server trả
`08 0001` rồi KICK. Hồi **FULL party** mỗi trận (không gác theo `alive<total` — con số đó vô nghĩa
vì đọc từ `state.allies` của leader).

## `party_song_that`

Đếm người sống của **cả party** bằng cách đọc thẳng từng client cùng party (`client.party_peers()`),
không qua `state.allies` của leader. Trả `None` khi không đọc được party (test / acc lẻ) → caller
quay về đường cũ.
