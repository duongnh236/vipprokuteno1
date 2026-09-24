# Bảng mã ngắt kết nối (S:000-000)

Nguồn: `client.py` `DISCONNECT_CAUSE` (~dòng 191). Server gửi `S:000-000 <斷線> +斷線原因(1)`
**trước khi** đóng kết nối. Layout gói: `[header 7B][sub 2B = 00 00][cause 1B]`.

Trước đây bot không đọc gói này → 1574 lần đứt trong một phiên mà chỉ biết "Server đóng kết nối".
Đọc ra mới thấy **78% là mã 90**.

| Mã | Nghĩa | Hành vi bot |
| --- | --- | --- |
| 1 | gửi dữ liệu quá nhiều | OFF riêng acc |
| 2 | sai câu hỏi 3 lần | OFF riêng acc |
| 3 | login sai 3 lần | OFF riêng acc |
| 4 | bị server kick | OFF riêng acc |
| 5 | sự kiện vi phạm | OFF riêng acc; nếu mode `event` → khóa mở event 15 phút (`event_blocked_until`) |
| 6 | sự kiện vi phạm | như trên |
| 7 | không tìm thấy sự kiện | OFF riêng acc |
| 8 | trigger ngoài dự kiến | OFF riêng acc |
| 9 | sai phiên bản bảng sự kiện | OFF riêng acc |
| 10 | lỗi trả bảng | OFF riêng acc |
| 11 | đi vào điểm chướng ngại | OFF riêng acc |
| 12 | bấm mìn không hợp lệ | OFF riêng acc |
| 13 | gửi gói liên tục quá nhanh | OFF riêng acc |
| 14 | di chuyển QUÁ XA | OFF riêng acc (xem `_move_chia_doan` / `MOVE_XA_TOI_DA`) |
| 15 | xóa thành công, khởi động lại | OFF riêng acc |
| 16 | IP đăng nhập không hợp lệ | OFF riêng acc |
| 17 | sai phiên bản, cần cập nhật | OFF riêng acc |
| 18 | sửa dữ liệu | OFF riêng acc |
| 19 | ĐĂNG NHẬP TRÙNG LẶP | OFF riêng acc |
| 20 | server bất thường | OFF riêng acc |
| 21 | lỗi thông tin file save | OFF riêng acc |
| 22 | sai định dạng gói | OFF riêng acc |
| 23 | đổi tên | OFF riêng acc |
| 24 | mật khẩu quá ngắn | OFF riêng acc |
| 25 | tên trùng | OFF riêng acc |
| 26 | sự kiện vi phạm | OFF riêng acc |
| 27 | lỗi đăng nhập | OFF riêng acc |
| 28 | phòng vệ | OFF riêng acc |
| 29 | dữ liệu đơn quá nhiều | OFF riêng acc |
| 30 | khóa tài khoản | OFF riêng acc |
| 31 | ID chưa được mở | OFF riêng acc |
| 32 | chiến đấu liền scene | OFF riêng acc |
| 33 | scene không khớp mốc | OFF riêng acc |
| 34 | trùng lặp liên server | OFF riêng acc |
| 35 | gửi gói đăng nhập liên tục | OFF riêng acc |
| 36 | ID ngoài phạm vi | OFF riêng acc |
| 37 | khác scene | OFF riêng acc |
| 38 | scene đích không khớp | OFF riêng acc |
| 40 | sửa gói hợp thành | OFF riêng acc |
| **42** | **sửa gói chiến đấu** | **RECONNECT** (`DISCONNECT_RECONNECTABLE`) |
| **47** | **kết thúc sự kiện khi trận chưa kết thúc** | **RECONNECT** |
| **60** | **SERVER TẮT MÁY BẢO TRÌ** | **OFF TẤT CẢ, KHÔNG reconnect** |
| 61 | thông báo riêng của server | OFF riêng acc |
| **90** | **ĐĂNG NHẬP QUÁ THƯỜNG XUYÊN (chặn tốc độ)** | relogin chậm dần: `30*attempt`, tối đa 300s |

## Quy tắc suy ra

- `DISCONNECT_RECONNECTABLE = frozenset((42, 47))` — chỉ hai mã này coi là lỗi phiên tạm thời.
- `DISCONNECT_RATE_LIMIT = 90`.
- `cause == 60` → `workflows/reconnect.py::stop_all_for_maintenance` (set stop mọi account, đóng
  socket; người dùng có thể Login lại sau khi bảo trì xong).
- `cause != 0` và không thuộc (42, 47) và không phải 60 → OFF riêng account, vào `ui_kicked_users`.
- Mã 5 khi `PARTY_CONFIG.mode == "event"` → khóa mở event 15 phút để phá vòng lặp mã 5.
