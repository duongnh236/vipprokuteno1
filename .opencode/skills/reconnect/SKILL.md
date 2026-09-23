---
name: Disconnect / Reconnect
description: Dùng khi làm việc với mất kết nối và tự động đăng nhập lại của ts_bot — mã ngắt kết nối S:000-000, half-open recv timeout, supervisor relogin vô hạn có backoff, phân biệt rớt mạng với relogin cố ý và với server bảo trì, phục hồi party sau reconnect.
---

# Disconnect / Reconnect

Bot chạy nền nhiều account; một account mất kết nối **không** được làm cả party đứng hình. Luồng
này: phát hiện rớt → đọc **lý do** server ngắt → quyết định relogin hay OFF → đăng nhập lại (có
backoff) → phục hồi party.

## Phát hiện rớt

Có 3 đường, đều set `client.server_closed = True` (trừ khi ta tự đóng):

| Đường | Chỗ | Ghi chú |
| --- | --- | --- |
| `recv` timeout quá lâu | `client.py::_recv_loop_impl` | `RECV_SOCK_TIMEOUT=30s` mỗi lần; không nhận gói nào > `RECV_DEAD_SECS=120s` → coi là **half-open** (server không gửi RST/FIN) → rớt |
| `recv` `OSError` | `_recv_loop_impl` | server reset; `_deliberate_close` thì bỏ qua |
| `recv` trả rỗng | `_recv_loop_impl` | server chủ động đóng |
| `send` lỗi | `client.py::send` | đặt `server_closed = True` (nếu không phải tự đóng) |

## Đọc lý do server ngắt

`S:000-000 <斷線> +斷線原因(1)` → `client.disconnect_cause` + `disconnect_reason`
(`client.py` ~4837, bảng `DISCONNECT_CAUSE` ở `client.py` ~191). Bảng đầy đủ:
`references/disconnect-codes.md`.

Ba mã quyết định hành vi:

| Mã | Nghĩa | Xử lý |
| --- | --- | --- |
| **42, 47** | sửa gói chiến đấu / kết thúc sự kiện khi trận chưa xong | **RECONNECT** (lỗi phiên tạm thời) — `DISCONNECT_RECONNECTABLE` |
| **60** | SERVER TẮT MÁY BẢO TRÌ | **OFF TẤT CẢ account, KHÔNG reconnect** (`stop_all_for_maintenance`) |
| **90** | ĐĂNG NHẬP QUÁ THƯỜNG XUYÊN (server chặn tốc độ) | relogin **chậm dần** (30×attempt, tối đa 300s) |

Mã khác (khác 0, khác 3 mã trên) → **OFF riêng account đó**, thêm vào `ui_kicked_users`, không
reconnect. Nếu là leader đang có `ui_train_target` → bật `ui_leader_recover`.

## Supervisor relogin

`run_party_digioi.py::_run_account_supervised` bọc `run_account`:

- Vòng **vô hạn** tới khi GUI Stop.
- Backoff: `1s` nếu forced, còn lại `5s` (≤3 lần) → `30s` (≤13) → `60s`.
- Mã 90: `wait = max(wait, min(30*attempt, 300))`.
- **Giãn cách khi relogin hàng loạt** (tránh mã 90): nếu ≥2 acc cùng party đang rớt → cộng thêm
  `8s * vị_trí_acc`; forced (ép đồng bộ) → `3s * vị_trí`. Bug thật: 5 acc login trong ~1s → dính 90.
- `ResyncSignal` (ép đồng bộ theo leader) và **lỗi luồng bất ngờ** đều đi đường relogin.
- Trong `run_account` cũng có nhánh chống 90 khi **chưa vào world** (`_rl_hits`, 30×, tối đa 300s) —
  vòng này nằm TRONG `run_account`, backoff supervisor không cứu được.

## Relogin "nhẹ" (`is_reconnect=True`)

`run_account(..., is_reconnect=True)`:
- **Bỏ qua** daily/gacha/mail/vantieu/exp (đã làm phiên trước) — tránh lệch nhịp leader.
- Phục hồi mục tiêu AUTO BATTLE đã chọn (`ui_train_target`); nếu đang ở bãi thì ra **safe** cho kéo.
- Resync vị trí thật qua `0x03` self-spawn.
- Member vào lại thì đợi leader; leader vào lại thì `ui_leader_recover` để gom lại.

## Relogin cố ý ≠ rớt

Nhiều lần đổi pha train phải relogin **có chủ đích**; nhìn giống "server đá". Phân biệt bằng
`account_forced_reconnect` (set + reason). Đừng log/nhầm thành rớt:
- `workflows/reconnect.py::force_supervisor(username, client, reason)` — ép supervisor relogin.
- Lý do điển hình: "chuyển pha TRAIN", "ép đồng bộ theo leader".

`force_supervisor` **từ chối** ép reconnect khi `client._daily_use_selected_pet` (daily đang chạy) →
giữ online.

## Phục hồi party

| Field | Ý nghĩa |
| --- | --- |
| `st["reconnecting"]` | set username đang rớt + login lại (chờ resync) |
| `ui_leader_recover` | leader rớt → member về thành chờ |
| `ui_member_recover` | member rớt → tự chạy lên bãi tìm safe gần team |
| `ui_recovery_safe_ready` | member đã đứng safe chờ leader đón |
| `ui_recovery_city_arrived` | đã về thành chờ leader online |
| `ui_kicked_users` | bị server kick (không reconnect) |
| `account_reconnect[user]` | supervisor báo acc này có reconnectable không |

Chi tiết phục hồi: `workflows/train.py::_android_train_recovery_tick` (leader loss → cả party về
thành; member loss → tự lên safe; leader ra safe đón rồi kéo ra bãi).

## Quy tắc

- **Không tự relogin chỉ vì không gặp quái** (kẹt vòng đăng nhập khi server chặn tốc độ).
- Mã 60 = bảo trì → OFF hết, **tuyệt đối không** quay vòng login.
- Mã 90 → **không** login lại ngay; chờ lâu dần.
- Rớt lúc bấm Stop / `_deliberate_close` → **không** phải rớt.
- `_run_account_supervised` phải bọc **mọi** lỗi luồng; lỗi không lường trước = relogin (có backoff),
  không để luồng chết âm thầm.
- Mở `run_account` nhẹ khi reconnect; không chạy full startup.

## Kiểm chứng

```bash
python3 -B -m unittest discover -s tests -q -p 'test_android_safety.py'
```

Test liên quan: `test_kick_42_and_47_are_reconnectable_but_maintenance_is_not`,
`test_daily_recovery_does_not_disconnect`, `test_map_train_config_and_no_idle_relogin`.

Nguồn chuẩn: `docs/android-workflows.md`, `docs/android-recovery.md`.
