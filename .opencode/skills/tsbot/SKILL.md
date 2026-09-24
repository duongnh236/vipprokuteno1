---
name: tsbot
description: Phát triển, gỡ lỗi hoặc tái cấu trúc dự án TSBOT Android/Python nhưng vẫn giữ nguyên hành vi đang chạy và phân tách rõ trách nhiệm của Train, Dị giới, Daily, party, reconnect, combat, UI và protocol. Dùng cho công việc triển khai hoặc kiến trúc trong kho mã TSBOT; không dùng cho dự án Android hoặc Python không liên quan.
---

# Phát triển TSBOT

Xem các luồng đang hoạt động là hợp đồng tương thích. Chỉ thực hiện thay đổi nhỏ nhất trong module sở hữu hành vi; không giải quyết một yêu cầu cục bộ bằng cách chèn logic nghiệp vụ vào bộ điều phối chung hoặc workflow không liên quan.

## Phương pháp làm việc

1. Xác định Git root đang hoạt động rồi kiểm tra hướng dẫn cục bộ, trạng thái repository, call site liên quan, nơi sở hữu state và các bài test. Không giả định cách viết hoa tên thư mục và không ghi đè thay đổi không liên quan đang có trong worktree.
2. Xác định đúng tầng sở hữu trước khi chỉnh sửa. Với thay đổi backend hoặc workflow, đọc [references/architecture.md](references/architecture.md). Truy vết cả bên gọi và bên sử dụng khi thay đổi state dùng chung, callback, packet hoặc vòng đời.
3. Mở rộng qua một hàm, trường state hoặc interface nhỏ thuộc module đó. Lưu state account theo slot ổn định hoặc username tùy ngữ cảnh; tuyệt đối không suy ra account từ tab đang hiển thị sau khi tác vụ bất đồng bộ đã bắt đầu.
4. Giữ nguyên các lời gọi bridge công khai và trường payload hiện có, trừ khi người dùng yêu cầu migration rõ ràng. Thêm wrapper tương thích khi chuyển phần triển khai giữa các module.
5. Kiểm tra ranh giới đồng thời. Một client không được có nhiều owner movement, reconnect, party hoặc combat cùng phát lệnh mâu thuẫn. Ưu tiên cơ chế ownership hoặc generation cancellation rõ ràng thay vì thêm `sleep` hay cờ global.
6. Xác minh hành vi vừa thay đổi và các invariant lân cận. Tối thiểu phải kiểm tra cú pháp/test Python và tác vụ compile/test Gradle Android phù hợp. Xem log thiết bị thật là bằng chứng, không phải quyền thay đổi các hành vi không liên quan.

## Ranh giới thay đổi

- Hành vi Train mới thuộc module Train; Dị giới có thể bàn giao sang Train nhưng không được sao chép phần triển khai nội bộ của Train.
- Daily điều khiển thứ tự và việc dừng; module dungeon và boss sở hữu cơ chế hoạt động tương ứng.
- Module party và channel sở hữu roster, lời mời, quân sư, gom lại đội và chuyển phân khu.
- Reconnect sở hữu chính sách phục hồi và bàn giao quyền điều khiển về workflow bị gián đoạn.
- Combat sở hữu quyết định mục tiêu và skill. `client.py` sở hữu thao tác packet cấp thấp và state client, không sở hữu chính sách workflow cấp cao.
- State UI phải độc lập theo account. Chốt slot và danh tính account trong callback trước khi phát tác vụ bất đồng bộ.
- Không thêm fallback âm thầm đưa account sang workflow khác. Mọi chuyển tiếp phải rõ ràng và có log.
- Button AUTO BATTLE chỉ bật tự động đánh, không điều khiển di chuyển.
- Button AUTO TRUY KÍCH chỉ điều khiển di chuyển theo hình số 8.

Khi thay đổi được yêu cầu xung đột với invariant đã thiết lập, hãy báo rõ xung đột và cập nhật hợp đồng của module sở hữu một cách có chủ đích, thay vì chồng thêm một ngoại lệ mới.
