# Kiến trúc TSBOT và ranh giới chống hồi quy

Đọc tài liệu này khi thay đổi backend workflow, vòng đời, protocol hoặc logic xuyên module. Với chỉnh sửa thuần giao diện, chỉ kiểm tra Android view và payload bridge của nó, trừ khi hợp đồng dữ liệu cũng thay đổi.

## Quyền sở hữu theo tầng

| Tầng/module | Sở hữu | Không được sở hữu |
|---|---|---|
| Android view và `MainActivity` | Render giao diện, state tương tác theo slot, định tuyến callback bất đồng bộ | Game protocol hoặc chính sách workflow |
| `agent_bridge.py` | API ổn định giữa Android và Python, tuần tự hóa JSON, kiểm tra đầu vào | Điều phối gameplay chạy dài |
| `run_party_digioi.py` | Registry runtime, state phiên dùng chung, dispatch workflow, entrypoint tương thích code cũ | Cơ chế Train/Daily/Dị giới mới |
| `workflows/train.py` | Gom đội, bàn giao việc lập party, dẫn tới map train, vòng đời farm | Thứ tự Daily hoặc nội bộ Dị giới |
| `workflows/digioi.py` | Vào Dị giới, vòng đời truy kích, bàn giao rõ ràng sang Train | Bản sao thứ hai của logic gom đội/train |
| `workflows/daily.py` | Thứ tự Daily, tính độc lập theo account, cơ chế dừng sau trận hiện tại | Cơ chế packet của boss/dungeon |
| `workflows/dungeon.py`, `boss.py` | Điều kiện và quá trình thực thi riêng của hoạt động | Reconnect toàn cục hoặc phục hồi Train |
| `workflows/party.py`, `channel.py`, `channel_regroup.py` | Mời, nhận lời, roster, quân sư, chọn và đồng bộ lại phân khu | Quyết định combat |
| `workflows/reconnect.py`, `lifecycle.py` | Phân loại disconnect, phục hồi và tiếp tục owner bị gián đoạn | Khởi động workflow không liên quan |
| `combat.py` | Chọn skill, mục tiêu và rule từ setting account hiện tại | Movement hoặc chuyển workflow |
| `client.py`, `protocol.py` | Socket packet, state đã parse, thao tác cấp thấp an toàn | Thứ tự hoạt động cấp cao |

## Các invariant không hiển nhiên

- Train, Dị giới và Daily là các owner workflow riêng biệt. Bàn giao là một chuyển tiếp rõ ràng; helper dùng chung không được khiến workflow này tự khởi động workflow khác.
- Thao tác UI account phải gắn với slot. Chốt `slot + expected username` trước khi dispatch nền, kiểm tra cả hai tại bridge và trả kết quả về đúng slot đã chốt.
- Movement chỉ có một owner trên mỗi client. Route mới hủy route cũ trước khi route cũ có thể gửi waypoint tiếp theo. Không sửa race condition của route bằng cách tăng thời gian chờ.
- Battle state chặn movement; state route phải tồn tại qua trận đánh và chỉ tiếp tục sau khoảng an toàn sau trận đã cấu hình.
- Mỗi combat decision worker phải sở hữu khóa bất biến `(generation, turn)` và snapshot option của
  chính lượt đó. Worker cũ không được gửi packet, xóa `available` hay reset cờ của lượt mới. Với
  tracker, chỉ `turn_start` của lượt mới được mở lại trạng thái “chưa đánh”; invariant này áp dụng
  giống nhau cho Dị giới solo nhiều pet và party team.
- Reconnect phục hồi state cho workflow sở hữu account trước khi disconnect. Chính sách kick hoặc bảo trì phải tách biệt với reconnect thông thường.
- Phục hồi party/phân khu phải có tính idempotent. Không liên tục giải tán party hợp lệ hoặc đổi phân khu chỉ vì dữ liệu dân số cache thay đổi.
- Setting độc lập theo account và được áp dụng tức thời ở nơi có hỗ trợ. Dashboard polling không được ghi đè editor đang thao tác hoặc trạng thái điều khiển lạc quan của từng account bằng snapshot cũ.
- Packet parser chỉ cung cấp dữ kiện; workflow quyết định chính sách. Trường packet chưa biết phải được capture hoặc ghi log trước khi gán ý nghĩa.

## Mẫu refactor an toàn

1. Xác định hành vi hiện tại của entrypoint công khai và state quan sát được.
2. Thêm hoặc củng cố test quanh invariant cần giữ.
3. Chuyển phần triển khai vào module sở hữu phía sau cùng entrypoint.
4. Giữ một wrapper tương thích mỏng khi caller vẫn dùng vị trí cũ.
5. Chỉ loại bỏ phần thực thi trùng sau khi đã tìm toàn bộ caller và background loop.
6. Kiểm tra workflow vừa đổi cùng các điểm bàn giao lân cận: Dị giới → Train, reconnect → workflow trước đó, Daily → dungeon/boss.

Tránh viết lại diện rộng `client.py` hoặc `run_party_digioi.py`. Chỉ tách một trách nhiệm mỗi lần và giữ hành vi packet ổn định, trừ khi bằng chứng packet yêu cầu thay đổi.

## Mức xác minh tối thiểu

- Compile các file Python đã đổi mà không ghi cache vào repository.
- Chạy bộ test Python của repository.
- Chạy tác vụ compile/test Gradle hẹp nhất có liên quan; chỉ build APK khi được yêu cầu hoặc cần kiểm tra trên thiết bị.
- Với lỗi timing, movement, reconnect hoặc packet, kiểm tra bằng log có timestamp và xác nhận chỉ một owner phát loại lệnh bị ảnh hưởng.
- Báo rõ phần đã xác minh và phần vẫn cần kiểm tra với game/server thật.
