# Vào Dị Giới — mã `S:097-001` và vì sao phải chờ

Nguồn: `client.py::enter_di_gioi`, `enter_di_gioi_safe`.

## Vì sao không bắn lại mù

Bản cũ: gửi `0x61` rồi ngủ `wait` giây, bắn tiếp **bất kể** server đã trả lời chưa → mỗi acc bắn 24
gói thay vì 1. Bình thường server rảnh nên không ai thấy, nhưng lúc server tải, khuyết tật **tự
khuếch đại**: càng chậm càng bắn, càng bắn càng chậm.

Đo thật 15/09:

| Đợt | Tải | Số acc | Số gói | Acc thất bại |
| --- | --- | --- | --- | --- |
| 10:14–10:18 | rảnh | 68 | 349 | 1 |
| 00:29–00:32 | tải | 65 | 629 | 26 |

`enter_di_gioi_safe` sửa: gửi `0x61` → **chờ `S:097-001`** (`_dg_enter_event`), không bắn thêm trong
lúc chờ.

## Hằng số

| Tên | Giá trị | Ý nghĩa |
| --- | --- | --- |
| `DG_CHO_TRA_LOI_SEC` | 30.0 | chờ tối đa `S:097-001` (server tải có lúc trả ~25s) |
| `DG_GIAN_KHI_IM_SEC` | 15.0 | server im hoàn toàn → giãn ra rồi thử lại, **không** bắn dồn |

## Mã `S:097-001`

| Mã | Nghĩa | Xử lý |
| --- | --- | --- |
| **0** | đồng ý | chờ server đổi map (kiểm `in_di_gioi()`) |
| **6** | đã ở trong DG rồi | như mã 0 |
| **1** | cấp không đủ | acc này **không bao giờ** vào được → bỏ, không bắn lại |
| **2** | hết giờ hôm nay | hết **thật**, lần **duy nhất** được phép kết luận hết giờ → bỏ |
| 3 | đang đánh | tạm thời → chờ rồi thử lại |
| 4 | đang sự kiện | tạm thời → chờ rồi thử lại |
| 5 | đang tổ đội | tạm thời; `enter_di_gioi()` đã rời đội nên lần sau sẽ qua |

Không nhận được gói nào → nói thẳng **"không biết"**, **không** đoán "hết giờ" (đã từng đánh dấu
xong DG oan trong khi acc còn nguyên 120/120 phút).

## Kiểm trước khi gửi

- `current_map is None` → chưa vào world xong → chờ.
- `in_combat()` → đang kẹt battle (login ngay bãi quái) → chờ hết trận.
- `party_members` khác rỗng → `enter_di_gioi()` tự `leave_party()` trước.

## Sau khi vào

- `in_di_gioi()` đọc `current_map == 49942` (map thật, **không** dựa số kênh).
- Spawn cố định `RUN_FALLBACK_ANCHOR (870,740)`; chốt `_di_gioi_anchor` cho run-around.
