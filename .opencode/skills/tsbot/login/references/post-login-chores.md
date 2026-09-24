# Việc vặt sau login

Chạy trong `run_party_digioi.py::run_account`, **chỉ khi `not is_reconnect`**. Reconnect nhẹ bỏ
toàn bộ khối này (đã làm ở phiên trước) để không lệch nhịp leader.

## Trước khối việc vặt

1. Nếu **đang đứng trên map train** (`login_map == start_city_id`) → `navigate_to(safe, flee=True)`
   **trước** khi làm việc vặt, để không đứng giữa bãi quái lâu rồi bị kéo vào trận.
2. `c.log_bag_delayed()` — in túi khi snapshot về + ổn định (tối đa ~8s).
3. **Gán config per-acc NGAY ở đây** (`auto_bag_clean`, `scroll_modes`, `material_modes`,
   `auto_event_exchange`, `event_exchange_items`, `auto_donate_materials`…). Nếu gán muộn (sau khối
   việc vặt) thì lúc gọi hàm chúng vẫn là mặc định → user tick mà bot **không** làm.

## Thứ tự việc vặt (giữ nguyên)

| # | Việc | Ghi chú |
| --- | --- | --- |
| 1 | `request_offline_exp()` | nhận exp offline (treo máy) nếu có |
| 2 | `claim_mail()` | nhận quà mail + xóa mail đã đọc |
| 3 | `claim_achievements()` | quà thành tựu (đọc bit forever-flags 0x51) |
| 4 | `claim_checkin()` | điểm danh hằng ngày |
| 5 | `claim_14day_gift()` | quà 14 ngày user mới (0x57) |
| 6 | `claim_event_14day()` | event tặng quà 14 ngày (0x7c) |
| 7 | `claim_legion_gift()` | quà quân đoàn hằng ngày |
| 8 | `claim_friend_gifts()` | tặng quà tất cả bạn + nhận quà bạn tặng |
| 9 | `decompose_junk_scrolls()` | phân giải cuộn gọi pet rác |
| 10 | `tu_mo_rong_tui()` | ⛔ **TẠM TẮT** (không gọi khi login) — hàm còn nguyên |
| 11 | `_tu_cong_diem()` | ⛔ **TẠM TẮT** (không gọi khi login) — hàm còn nguyên |
| 12 | `_tu_nang_skill()` | ⛔ **TẠM TẮT** (không gọi khi login) — hàm còn nguyên |
| 13 | `_kiem_han_ba_dau()` | Bá Đầu sắp hết hạn → báo UI |
| 14 | `auto_upgrade_pet_skills()` | ⛔ **TẠM TẮT** (không gọi khi login) — hàm còn nguyên |
| 15 | `process_furnace()` | soi lò + mua/notify theo config per-acc |
| 16 | `donate_legion()` | donate nguyên liệu quân đoàn (dọn túi) |
| 17 | `tu_mo_hop_trang_bi()` | mở rương trang bị → phân giải / donate / vứt |
| 18 | `deposit_fashion_to_collection()` | thả đồ thời trang vào Bộ Sưu Tầm |
| 19 | `use_login_items()` | dùng item trong `use_items.json` |
| 20 | `do_mount_upgrade()` | nâng thú cưng bằng viên kỳ đơn (LUÔN bật) |
| 21 | `use_phuc_than_items()` | dùng Phục Thần (bỏ qua mode `event`) |
| 22 | `do_van_tieu()` | vận tiêu (bật/tắt theo acc) |
| 23 | mua shop | Hộ Phù / Hộp Thiên Châu / Triệu Gọi Bảo Hộp (theo RoleCount 0x55) |
| 24 | `buy_hp_sp()` | mua HP/SP ở Trác Quận nếu dự trữ < ngưỡng |
| 25 | `do_legion_boss()` | boss quân đoàn solo nếu còn lượt + hết cooldown |

> **Đang tạm tắt 10/11/12/14:** trong `run_party_digioi.py::run_account` chỉ **comment phần GỌI**;
> các hàm `tu_mo_rong_tui` (client), `_tu_cong_diem`, `_tu_nang_skill` (run_party_digioi),
> `auto_upgrade_pet_skills` (client) **vẫn còn nguyên** — bỏ comment khối tương ứng để bật lại.

## Bỏ qua có điều kiện

- **Mode `event`** (40NPC / 2K): bỏ `do_daily`, `auto_world_boss`, `auto_team_dungeon`,
  `do_legion_boss`, **và Phục Thần** (vào event không ăn hệ số EXP này → phí item).
- **Train/DG workflow độc lập** (`_isolated_train_dg`): bỏ daily / world boss / team dungeon /
  boss quân đoàn login — acc dành trọn cho train.
- `auto_open_boxes`, `auto_bag_expand`, `auto_buy_shop`, `buy_hp`, `buy_sp`: mặc định **TẮT**.

## Bẫy đã gặp

- Dùng biến `mode` trong khối việc vặt → **`UnboundLocalError`** vì `mode` được gán muộn hơn; phải
  dùng `_early_mode`. Lỗi này từng làm thread `run_account` chết → **cả party thoát**.
- `buy_hp_sp` **đổi map** (Trác Quận → map NPC → về) → phải cập nhật lại `login_map`, không thì các
  nhánh sau tưởng acc còn ở bãi train và **không kéo về**.
- Gán config per-acc muộn → user tick mà bot không làm (bug thật với giải cuộn rác / donate nguyên
  liệu / bán Nội Đạt).
- Phục Thần dùng đúng **lúc login** (còn ở thành/điểm login), tránh dùng giữa lúc đang combat ngoài bãi.

## Điều phối sau việc vặt

Sau việc vặt mới chạy tới map/điểm tập kết, sync kênh, rồi mở gate hoạt động. Mode Train/DG do
workflow sở hữu (`ui_train_target`) — không để lộn với việc vặt login.
