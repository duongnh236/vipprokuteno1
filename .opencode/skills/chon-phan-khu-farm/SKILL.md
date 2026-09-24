---
name: Chọn phân khu farm
description: Dùng khi làm việc với việc chọn/chuyển KÊNH (phân khu) farm của ts_bot — AUTO chọn kênh vắng hay ghim kênh thủ công, mã lỗi kênh, đồng bộ kênh cả party, gom lại khi lệch kênh, và fallback khi kênh đầy.
---

# Chọn phân khu farm (kênh)

Kênh (phân khu) **thuộc từng map**; leader chốt kênh, cả party chuyển theo. Đổi kênh phải **hết trận
+ ra safe** và **rời tổ đội** mới gửi được.

## Điểm vào

| Việc | Chỗ code |
| --- | --- |
| Bridge chính sách (AUTO / ghim manual) | `agent_bridge.py::set_train_channel_policy_json` |
| Bridge liệt kê kênh | `agent_bridge.py::channels_json` / `_channel_rows_for_map` |
| Bridge đổi kênh cả team | `agent_bridge.py::switch_channel_json` → `run_party_digioi.py::party_switch_channel` |
| UI | `AccountManagerView.java::renderLeaderChannelPolicy` (đọc `channel_options`, `channel_auto/manual`) |
| Gửi lệnh đổi kênh | `client.py::switch_channel` (`0x07 0200 + channel u16`), lock 1 lệnh/lúc |
| Ack / danh sách | `client.py::_on_channel_switch_result` / `_on_channel_list` (`0x07 0100`) |
| Điều phối chốt + thi hành | `run_party_digioi.py::_dieu_phoi_chot_kenh`, `_dieu_phoi_thi_hanh_kenh`, `do_channel_sync` |
| Qua cổng ⇒ bỏ ghim kênh | `workflows/train.py::_train_adopt_map_channel` |
| Kênh đầy (retry / fallback) | `workflows/train.py::_train_retry_leader_channel`, `_train_fallback_full_channel` |
| Gom lại do lệch kênh | `workflows/channel_regroup.py::request/tick` (owner: `workflows/channel.py`) |

## State chính

`client.channels` (`{kênh:(số_người,sức_chứa)}`), `current_channel`, `kenh_dang_nghi_ngo`,
`_chan_switch_result`, `_ds_kenh_map`.
`_pstate`: `kenh_dich`, `kenh_ghim`, `train_channel_auto`, `train_channel_manual`, `train_channel_map`,
`manual_train_channel(_ready)`, `auto_best_channel`, `train_channel_regroup`.

## Quy tắc / gotcha

- **Kênh thuộc 1 map** — mỗi map danh sách kênh khác nhau; **qua cổng phải BỎ ghim kênh**.
- **Mã kết quả**: `0` OK, `1` trùng kênh, `2` không tồn tại (`沒有該分區`), `3` đang tổ đội, `4` kênh đầy
  (`分區人數已滿`); `-1` = timeout do bot tự đặt.
- **Member không tự chuyển kênh** — khi `ui_train_phase=="farming"` phải qua `party_switch_channel`
  (safe → tan PT → đổi → lập lại), không switch trực tiếp.
- **Phải hết trận + ra safe** trước khi đổi kênh; **không** đổi kênh khi đang đánh event/loạn đấu.
- **Không set `current_channel` trước ack server**; `kenh_that` **không hỏi lại** được (server chỉ push).
  Kênh "nghi ngờ" sau lệnh hỏng → không dùng để kết luận lệch kênh.
- Manual **ưu tiên tuyệt đối** (bỏ auto); auto **bỏ qua** ghim manual.
- Chỉ chọn **kênh vàng khi ĐÃ tới bãi train**, không đổi ngay lúc tick.
- Kênh đầy mã 4 / không tồn tại mã 2 → retry/fallback; **tất cả kênh đầy** → giữ đích, chờ chỗ.
- AUTO chọn kênh đã **tắt toàn cục** (`pick_best_channel` return 0) — chính sách đến từ UI.

## Kiểm chứng

```bash
python3 -B -m unittest discover -s tests -q -p 'test_channel_regroup.py'
python3 -B -m unittest discover -s tests -q -p 'test_android_safety.py'
```
Test: `test_channel_policy_never_ranks_population`, `test_farming_channel_change_queues_safe_flow_not_direct_switch`,
`test_full_channel_fallback_requires_fresh_capacity_for_entire_team`,
`test_train_channel_full_requests_safe_regroup_without_relogin`,
`test_farm_map_replaces_city_pin_without_leaving_party`.
