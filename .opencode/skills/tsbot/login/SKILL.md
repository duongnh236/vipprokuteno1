---
name: Login
description: Dùng khi làm việc với luồng đăng nhập của ts_bot — HTTP login lấy user_id/access_token, gói auth TCP 0x01, chờ vào world, chuỗi setup combat-active, các việc vặt sau login, login riêng/LOGIN ALL, và phân loại lỗi đăng nhập.
---

# Login

Đăng nhập một account gồm **2 tầng**: HTTP login (lấy credential) rồi TCP auth (vào world). Sau
khi vào world mới chạy **chuỗi setup combat-active** và **việc vặt sau login**. Login **không** tự
chạy farm/daily.

## Luồng

1. **HTTP login** — `train_bot/login.py::login(username, password, device_id)` → `{user_id,
   access_token, username}`. `device_id` **sinh riêng mỗi account** (`_device_id_for`, md5 32 hex)
   để server không coi nhiều acc chung một device.
2. **TCP auth** — `GameClient.connect()`: `_open_game_socket` → `sock.sendall(build_auth_packet(...))`.
   `auth.py::build_auth_packet(user_id, access_token, server_id)`, `server_id` 1/2 theo `servers.json`.
3. **Chờ vào world** — chờ `c.self_entity is not None and c.current_map is not None` (tối đa ~15s).
4. **Setup combat-active** — `client._login_setup()` gửi chuỗi C2S mà client thật gửi ngay sau auth
   (0x19, 0x2b, 0x01, 0x7c, 0x41, 0x0c, 0x57, 0x62×2, 0x41 machinebox). Thiếu chuỗi này → char kết
   nối nhưng **không combat-active** → quái map thường **ngơ**, không aggro.
5. **Việc vặt sau login** — chỉ khi **không** phải reconnect: xem `references/post-login-chores.md`.

## Điểm vào

| Việc | Chỗ code |
| --- | --- |
| HTTP login | `train_bot/login.py::login` (`LoginError.error_code`) |
| Gói auth TCP | `train_bot/auth.py::build_auth_packet` |
| Kết nối + setup | `client.py::GameClient.connect` → `_login_setup` |
| Vòng login đầy đủ | `run_party_digioi.py::run_account` (đầu hàm) |
| Supervisor relogin | `run_party_digioi.py::_run_account_supervised` |
| Khởi động 1 acc | `run_party_digioi.py::start_account` |
| Khởi động party | `run_party_digioi.py::start_party` |
| Entry Android | `agent_bridge.start_json(payload)` (từ `MainActivity.startOne` / `loginAll`) |
| Login riêng 1 acc | `agent_bridge.start_json` với `only_user` (mode `stand`, `map_id=0`) |
| Lấy pet & skill sau login | `agent_bridge.skills_json(username)` (UI tự gọi sau 10s và 20s) |
| Logout an toàn | `agent_bridge.safe_logout_all_json` / `stop_one_json` |

## Phân loại lỗi (rất quan trọng)

| Tình huống | Nhận biết | Xử lý |
| --- | --- | --- |
| Lỗi mạng HTTP / cổng ephemeral (WinError 10048…) | `login()` bắt `URLError/OSError` | retry **6 lần**, chờ `min(30, 3*(n+1))s` |
| `error_code == 1` | `LoginError.error_code` | coi là lỗi tạm, nghỉ `LOGIN_ERR1_RETRY_MIN..MAX`, **không tính là fail** |
| Server chặn tốc độ (mã 90) | `c.disconnect_cause == 90` | nghỉ `30*attempt` (tối đa 300s), **không** login lại ngay |
| Server kick khi login | `c.disconnect_cause` khác 0 | **OFF, không retry** phiên đó |
| Login/connect lỗi 6 lần | `ok == False` | `_login_failed=True` → **supervisor thử lại** (backoff), không để nick chết |
| Chưa vào world | `self_entity`/`current_map` còn None | thử lại (tối đa 15s), rồi login lại |

Chi tiết mã ngắt kết nối: xem skill `reconnect` (`references/disconnect-codes.md`).

## Login riêng vs LOGIN ALL

- **Login riêng khi party đang chạy = REJOIN**, không tạo session mới. `agent_bridge.start_json`
  giữ nguyên toàn bộ runtime (mode/map/kênh đang chạy), chỉ cập nhật mật khẩu + start đúng acc vừa
  out. Payload nút Login cố ý để `mode=stand, map_id=0` — **đừng** đem nó `setup_party_runtime` (sẽ
  kéo cả leader về thành mặc định rồi đứng im).
- **LOGIN ALL** chỉ **bổ sung account đang offline**, không restart team, không reset bãi farm.
- Acc **đã online** thì nút Login bị khóa; LOGIN ALL bỏ qua acc đang chạy.

## Chuỗi setup combat-active (`_login_setup`)

- Gửi `0x41 0200` (tạm dừng hộp máy) rồi cuối chuỗi `0x41 0100 + machinebox_payload()` (bật lại).
  Server ACK `S:065-002`; handler phải biết đó là ACK của chính mình, không thì chèn gói bật-lại vào
  giữa chuỗi login.
- `machinebox_payload()` mang 2 cờ "chết → về thành" của char/pet (mặc định BẬT, giống client thật).
  **Phải set cờ này TRƯỚC `connect()`** vì chuỗi `0x41` được gửi ngay trong `connect()`.
- `combat_ready()` = gửi **lại toàn bộ** chuỗi setup; `rearm_ready()` = **chỉ** `0x41` (dùng khi chỉ
  cần "sẵn sàng" sau khi qua cổng, không đụng 0x7c/0x62).
- `combat_ready()` **thoát ngay** nếu `_auto_battle_enabled` là False — workflow Train/Daily/DG
  không được tự bật đánh.

## Quy tắc

- **Không tự relogin chỉ vì không gặp quái** — server chặn tốc độ đăng nhập (mã 90) → kẹt vòng login.
- Mã 90 → **không** login lại ngay; chờ lâu dần.
- Reconnect (`is_reconnect=True`) dùng đường **nhẹ**: bỏ qua daily/gacha/mail/vantieu/exp (đã làm
  phiên trước) để không lệch nhịp leader.
- Mật khẩu lưu cục bộ, **hiện chưa mã hóa chuyên biệt**.
- Login xong cache lại danh sách pet/skill (`login_gen` tăng) — dùng cho UI "Lấy pet & skill".

## State / cờ

| Field | Ý nghĩa |
| --- | --- |
| `account_clients[user]` | client đang chạy (GUI đọc trạng thái) |
| `account_threads[user]` / `account_stops[user]` | thread + stop event của acc |
| `is_account_running(user)` | đang có worker sống |
| `st["login_gen"]` | tăng mỗi lần vào world → UI cache lại pet/skill |
| `st["reconnecting"]` | acc đang rớt + login lại |
| `client._username` / `_label` | key config theo acc / tên hiển thị (tên nhân vật sau khi resolve) |
| `_login_failed` / `_unexpected_error` | cờ nội bộ → supervisor relogin |
| `login_map` | map lúc login (đọc sớm, ít bị nhiễu) |

## Kiểm chứng

```bash
python3 -B -m unittest discover -s tests -q -p 'test_android_safety.py'
```

Test liên quan: `test_ui_account_controls_follow_connection_state`,
`test_selected_pet_wins_across_all_workflows_with_default_fallback`,
`test_map_train_config_and_no_idle_relogin`, `test_team_json_is_bounded_and_omits_credentials`.

Nguồn: `README.md` (mục Đăng nhập/Đăng xuất), `docs/android-workflows.md`.
