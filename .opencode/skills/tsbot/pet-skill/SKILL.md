---
name: Pet & Skill
description: Dùng khi làm việc với tab PET & SKILL của ts_bot — chọn pet ra trận, skill nhân vật/pet, rule đánh theo số quái, cấu hình skill đặt tên/lưu theo pet, ngưỡng hồi HP/SP, Phục Thần, và logic combat quyết định skill mỗi lượt.
---

# Pet & Skill

Chọn pet xuất chiến + cấu hình **rule skill** (condition/skill/target) cho tướng và từng pet; cấu
hình lưu theo account và được `combat.py` dùng để ra quyết định mỗi lượt.

## Điểm vào

| Việc | Chỗ code |
| --- | --- |
| UI tab Tướng + 4 pet | `AccountManagerView.java::renderCombatEntitySettings` |
| Lưu cấu hình | `agent_bridge.py::apply_combat_settings_json` → `run_party_digioi.py::apply_account_battle` |
| Lấy skill/pet để render | `agent_bridge.py::skills_json` → `run_party_digioi.py::account_skills` → `client.py::skills_snapshot` |
| Đổi pet ra trận | `client.py::switch_pet` (`0x13 0100 + pid u16`) |
| Pet theo vai | `client.py::ensure_pet_role`, `_pet_role` |
| Áp ngưỡng hồi HP/SP | `run_party_digioi.py::apply_account_heal` |
| Rule + quyết định | `combat.py::_battle_rules`, `_custom_decision`, `_rule_condition_ok`, `_combat_attack`, `decide_char/pet/multipet` |
| Chọn skill | `combat.py::pick_combo_skill`, `pick_boss_skill`, `pick_alltarget_skill`, `pick_sp_restore_skill`, `pick_protect_skill`, `pick_cc_skill` |

## Config / state

`config.py`: `ACCOUNT_BATTLE`, `ACCOUNT_HEAL`, `ACCOUNT_PHUC_THAN`, `ACCOUNT_DAI_PHUC_THAN`,
`ACCOUNT_AUTO_MODE`, `ACCOUNT_CHAR_DEFEND`. (`ACCOUNT_SELECTED_PET` **tạo động** trong `agent_bridge.py`.)
`state.battle_config` dạng `{char:{...}, pet:{...}, pets:{<pid>:{...}}}`.
Skill IDs: `SKILL_NORMAL=10000`, `SKILL_HEAL_ALL=11010`, `SKILL_HEAL_ONE=11004`, `SKILL_DEFEND=17001`, `SKILL_FLEE=18001`.
Ngưỡng: `HEAL_HP_THRESHOLD=0.70`, `SP_RESTORE_THRESHOLD=0.5`, `SUPPORT_RESERVE_SP=100`, `PET_FIRE_MIN_SP=65`.

## Luồng UI → bridge

`apply_combat_settings_json(username, pet_id, char_skill, pet_skill, hp_percent, sp_percent,
use_phuc_than, char_mob_min, pet_mob_min, use_dai_phuc_than, pet_hp_percent, pet_sp_percent,
use_digioi_ho_phu, auto_buy_bao_hop)`:
- `char_skill=0` → auto; `-1` → rule `always normal`; `>0` → rule
  `{"condition":"mob","op":"gte","value":char_mob_min,"skill":char_skill,"target":"auto"}` + fallback `always normal`.
- Pet lưu vào `battle["pets"][str(pid)]`, **giữ rule 3 pet còn lại**; `pet_id=0` = tab Tướng.

## Quy tắc / gotcha

- **Rule first-match**: duyệt theo thứ tự, rule đầu khớp condition thắng; `skill="auto"` → trả về
  logic built-in.
- Skill **chưa học** hoặc **thiếu SP** → bỏ qua rule đó.
- Combo: `cat==1` và `splash ∈ {2,3,4}`; `splash=4` cần **block 3**, còn lại cần **block 2**. All-target `splash=8`.
- **Quest mode** (`>6` quái): all-target → combo → đánh thường; `≤6` → như boss + target ít máu nhất.
- Unit có skill hồi và `sp <= SUPPORT_RESERVE_SP(100)` → đánh thường để dành SP.
- **Gate `enemy_gen`**: chỉ đánh khi có dữ liệu quái mới (`0x33` thật); hết quái → không gửi atk.
- Format **per-pet**: pet chưa cấu hình = auto, **không** rơi về bộ "pet" chung.
- **Không đổi pet giữa trận**; không đổi sang pet không mang theo; pet mới vào hồi full HP/SP.
- Đặc kỹ pet chỉ dùng khi đã mở (`pet_special_skill[pid]`) và có data.
- Điều phối: 1 heal/lượt (con SP cao nhất); nhiều target chết → nhiều caster hồi sinh.

## Kiểm chứng

```bash
python3 -B -m unittest discover -s tests -q -p 'test_android_safety.py'
```
Test: `test_selected_pet_wins_across_all_workflows_with_default_fallback`.

Dữ liệu: `pets.json`, `skills_data.json`, `npc_special_skill.json`, `pet_stats.json`, `pet_hedoanh.json`.
