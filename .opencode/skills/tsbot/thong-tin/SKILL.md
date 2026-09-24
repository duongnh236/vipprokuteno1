---
name: Thông tin
description: Dùng khi làm việc với tab THÔNG TIN của ts_bot — chỉ số nhân vật/pet, vàng/tiền, EXP và tiến độ cấp, hiệu suất farm EXP/giờ, tiến độ daily, cài đặt chết-về-thành, công tắc AUTO, và bảng AGI/level party.
---

# Thông tin

Tab 👤 THÔNG TIN tổng hợp chỉ số mỗi account. Nguồn chính là `accounts_dashboard_json`.

## Điểm vào

| Việc | Chỗ code |
| --- | --- |
| Render tab (sectionMode=0) | `AccountManagerView.java::renderInfo` |
| Panel HP/SP/EXP tướng + pet | `AccountManagerView.java::gameStatusPanel`/`gameBar` |
| Hiệu suất EXP/giờ | `AccountManagerView.java::renderExpRate` |
| Tiến độ daily | `AccountManagerView.java::renderDailyProgress`/`progressLine` |
| Cài "chết về thành" | `AccountManagerView.java::renderDeathSettings` → `agent_bridge.py::apply_death_settings_json` |
| Nút AUTO BATTLE/TRUY KÍCH | `renderAutoButtons` → `agent_bridge.py::set_auto_mode_slot_json` |
| Nguồn dữ liệu | `MainActivity.java::refreshAccountsDashboard` → `agent_bridge.py::accounts_dashboard_json` |
| Bảng AGI/level party | `MainActivity.java::showPartyStats` → `agent_bridge.py::party_stats_json` |
| Daily status | `MainActivity.java::refreshDailyStatus` → `agent_bridge.py::daily_status_json` |
| State per-account | `run_party_digioi.py::account_status`; AGI party `party_agi_report` |

## Field chính (`accounts_dashboard_json`)

`level`, `hp/hp_max/sp/sp_max`, `pet_hp/pet_hp_max/pet_sp/pet_sp_max`, `pet_id`, `pet_level`, `pet_name`,
`pet_exp_current/pet_exp_level_total/pet_exp_level_remaining`,
`exp_current`, `exp_in_level`, `exp_level_total`, `exp_level_remaining`, `exp_rate`,
`gold`, `money`, `xu` (`premium_xu`), `currency_probe`,
`legion_boss_current/max/next`, `world_boss_current/max`, `solo_dungeon_remaining`,
`team_dungeon_remaining{20,50,80,110}`, `daily_progress_synced`,
`death_return`, `use_phuc_than`, `use_dai_phuc_than`, `phuc_than_remaining`,
`auto_battle_enabled`, `auto_pursuit_enabled`, `area_name`, `city_name`, `channel`,
`party_count/party_expected`, `train_map/train_x/train_y`.

- `exp_rate` (`client.py::exp_rate_snapshot`): `session_seconds`, `battles`, `battles_per_hour`,
  `char_exp_per_hour`, `pet_exp_per_hour`, `char_exp_total`, `pet_exp_total`, `last_battle_*`.
- `party_stats_json`: `avg_level`, `agi_min/max/spread`, `warning` (lệch AGI >10), `faith_thap[]`
  (pet trung thành <40), `members[]`.

## Quy tắc / gotcha

- `_level_exp_values` cấp không có trong bảng → trả `(None,None,None)`, **KHÔNG đoán**
  (`test_unknown_exp_level_not_guessed`).
- `char_exp` = EXP **tổng tích lũy**; `exp_in_level = char_exp - base[level]` (UI phải trừ mốc đầu cấp).
- Pet chuyển sinh (id `45000..45999`) dùng bảng EXP riêng.
- Dashboard xếp **5 slot cố định** theo `_account_slots`, không theo thứ tự configured.
- `account_status`: `log_label` (không phải `char`) mới dùng để mask log; `channel` lấy
  `current_channel` thật.
- `renderDailyProgress`: `daily_progress_synced=False` → cảnh báo server chưa gửi bảng nhiệm vụ 0x18.
- `status_json` (bridge) và `renderCombatLog` (Java) là **code chết**.

## Kiểm chứng

```bash
python3 -B -m unittest discover -s tests -q -p 'test_android_safety.py'
```
Test: `test_unknown_exp_level_not_guessed`. Dữ liệu: `pet_stats.json`, `skills_data.json`, `cities.json`.
