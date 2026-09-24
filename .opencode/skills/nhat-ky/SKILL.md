---
name: Nhật ký
description: Dùng khi làm việc với tab NHẬT KÝ của ts_bot — log hoạt động per-account (trận/EXP/nhặt đồ/dùng item/Phục Thần), nhật ký TEAM + export JSON, các hàm ghi log và gotcha về cập nhật EXP trễ.
---

# Nhật ký

2 loại: **nhật ký per-account** (tab ⚔ NHẬT KÝ) và **nhật ký TEAM** (panel trên tab Điều khiển).

## Per-account

| Việc | Chỗ code |
| --- | --- |
| Render tab (sectionMode=2) | `AccountManagerView.java::renderActivityLog` |
| Nguồn JSON | `agent_bridge.py::accounts_dashboard_json` → `accounts[i].activity_log` (+ `combat_exp_log`) |
| Hàm ghi log | `client.py::_metrics_battle_end`, `_metrics_exp_gain`; loot/use/phuc_than rải trong `client.py` |
| Thống kê EXP/giờ | `client.py::exp_rate_snapshot` |

**Dữ liệu**:
- `client.activity_log` = `deque(maxlen=200)`, `combat_exp_log` = `deque(maxlen=100)` — **trên RAM, KHÔNG persist**; bắt đầu từ lúc login.
- Record theo `type`: `battle_summary` (time/message/char_exp/pet_exp/seconds), `battle_exp`
  (who/name/pet/exp/confirmed), `exp` (who/pet/kind/exp/source), `phuc_than`, `loot`, `use`.

## Nhật ký TEAM

| Việc | Chỗ code |
| --- | --- |
| Poll + hiện | `MainActivity.java::refreshStatus` (2.5s) → `agent_bridge.py::team_debug_json` |
| Xem full / export JSON | `MainActivity.java::showFullTeamLog` / `onActivityResult` (requestCode 716) |

`team_debug_json` trả `coordination{...}` + `accounts[{user,online,name,area,map,position,channel,activity,phase,...}]` + `logs[]`.
- Chỉ đọc **256KB cuối** file log, **redact** credential (`password|token|authorization|...`),
  bỏ dòng "PET EXP probe", giữ **300 dòng cuối**, cắt mỗi dòng 1500 ký tự.

## Quy tắc / gotcha

- Packet EXP có thể tới **trễ ≤5s** sau trận → cập nhật lại đúng dòng `battle_summary`/`battle_exp`
  thay vì tạo dòng mới.
- Fallback lấy chênh lệch `char_exp` đầu/cuối trận **chỉ khi chưa đếm được EXP** (tránh cộng hai lần).
- `exp=0 + confirmed=False` = server chưa cấp (không phải parser đoán).
- `exp_rate_snapshot` tính EXP/giờ từ trận đầu tiên, **gồm cả thời gian nghỉ** giữa trận.
- `renderCombatLog` (Java) và `status_json` (bridge) là **code chết** — Android không gọi.

## Kiểm chứng

```bash
python3 -B -m unittest discover -s tests -q -p 'test_android_safety.py'
```
Test: `test_team_json_is_bounded_and_omits_credentials` (log ≤300 dòng, loại credential).
