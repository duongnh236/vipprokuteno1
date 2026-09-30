---
name: Chọn phân khu 40NPC
description: Dùng khi làm việc với chọn/chuyển PHÂN KHU (kênh) cho event 40 NPC của ts_bot — AUTO dò khu vắng đủ chỗ cho cả team, MANUAL ghim 1 khu + toast khi không đủ chỗ, đổi khu theo flow an toàn (ra safe → rời PT → đổi → gom lại), cập nhật dropdown live, và vòng dò lại khi khu vừa bị lấp đầy.
---

# Chọn phân khu 40NPC

40NPC chạy trên **map event** (mặc định `10991`) — map này có **danh sách kênh THẬT** (`S:007-001`,
~49 kênh), khác kênh thành. Vì event rất đông, phải chọn khu **vắng nhất đủ chỗ cho CẢ TEAM** rồi
đưa cả team qua **cùng lúc**, sau đó leader mới gom PT và chạy luồng 40NPC.

Chính sách này **ĐỘC LẬP** với phân khu farm (`chon-phan-khu-farm`): state riêng, selector riêng.

## Điểm vào

| Việc | Chỗ code |
| --- | --- |
| Bridge chính sách (AUTO / ghim MANUAL) | `agent_bridge.py::set_event_channel_policy_json` |
| Bridge toast Python → UI | `agent_bridge.py::poll_ui_notices_json` + `train_bot/ui_notice.py` |
| UI selector | `AccountManagerView.java::renderLeaderEventChannelPolicy` (đọc `event_channel_options`, `event_channel_auto/manual/status`) |
| Quyết định khu khi đã vào map event | `run_party_digioi.py::_chot_kenh_40npc` (gọi từ picker `do_channel_sync`) |
| Cờ "đang bật chính sách" | `run_party_digioi.py::_event_channel_policy_active` |
| Toast khi MANUAL không đủ chỗ | `run_party_digioi.py::_bao_khong_du_cho_40npc` |
| Đổi khu an toàn | `client.py::switch_channel` (bắt buộc đã rời PT) |
| Danh sách kênh live | `run_party_digioi.py::_lam_moi_ds_kenh`, `_bang_kenh` (`S:007-001`) |

## State (`_pstate(0)`)

- `event_channel_auto` (bool): bật AUTO dò khu vắng.
- `event_channel_manual` (int): khu user ghim (0 = chưa ghim).
- `event_channel_pick` / `event_channel_map`: khu picker đã chốt + map của nó (kênh thuộc từng map).
- `event_channel_status` (chuỗi `auto:N` / `manual:N`): hiển thị ở UI.
- `event_channel_notice_sig` / `event_channel_notice_at`: chống spam toast (30s).

## Luồng

1. User chọn ở **tab leader → "📡 CHỌN PHÂN KHU 40NPC"**, bấm **ÁP DỤNG**:
   - AUTO → `set_event_channel_policy_json(True, 0)` (chỉ lưu, KHÔNG đổi khu ngay).
   - MANUAL → `set_event_channel_policy_json(False, khu)`; bridge kiểm tra live, không đủ chỗ → trả
     `ok=false` để UI toast ngay.
2. User bấm **40 NPC** (`agent_bridge.start_event_json` → mode event, `npc40_force`).
3. Cả team `go_to_event` → vào map event (mỗi acc có thể khác khu/instance).
4. Vào `do_channel_sync`, **picker = leader** gọi `_chot_kenh_40npc`:
   - **AUTO**: `_bang_kenh` → chọn `min((số_người, kênh))` trong các kênh **còn ≥ số thành viên**,
     **loại kênh vừa bị server báo đầy/không tồn tại** (`_doc_ket_qua_doi_kenh`). Leader
     `switch_channel(khu, theo_lenh=True)`; member theo `channel_ready` qua cùng khu (barrier).
   - **MANUAL**: dùng `event_channel_manual`; nếu không có/không đủ chỗ → `_bao_khong_du_cho_40npc`
     (toast) và **chờ** user chọn lại (không tự đổi khu khác).
   - **Mặc định (không AUTO, không MANUAL)**: **hội tụ về kênh hiện tại của leader** (kéo member
     đang ở kênh khác về). Trên map event, party trây kênh = KHÔNG BAO GIỜ lập được → luôn phải
     hội tụ 1 kênh, nên `_event_channel_policy_active` **luôn bật cho 40NPC** (AUTO chỉ quyết định
     chọn kênh nào).
5. **Leader cũng chạy lại picker khi có RE-SYNC**: `VIEC_DONG_BO` → `resync_gen` bump → **cả leader
   lẫn member** chạy lại `do_channel_sync` (trước đây chỉ member → leader không chọn lại kênh →
   member chờ `channel_ready` mãi → kẹt 1 người 1 kênh).
5. Khu vừa chọn bị người khác lấp đầy (server trả mã 4) → kênh đó vào "sổ đen" tạm thời, picker
   **dò lại** khu khác (AUTO). MANUAL thì toast để user chọn lại.
6. Đồng bộ xong (cả team cùng map + khu) → leader gom PT → `npc40.run_loop`.
   - **Gồm USER NGOÀI**: nếu đã bấm **ÁP DỤNG MỜI NGOÀI**, leader mời user ngoài và **chờ tối đa 5
     phút** trước khi vào sự kiện (`_cho_user_ngoai_vao_party`, gọi trong nhánh gom đội event).
   - **Sức chứa khu tính cả user ngoài**: `need = số acc + 1` khi bật mời ngoài, nên khu AUTO/MANUAL
     chọn ra luôn đủ chỗ cho cả team gồm người ngoài.

## Quy tắc / gotcha

- **Kênh thuộc từng map**: chỉ chọn sau khi **cả team đã vào map event**; kênh thành vô nghĩa.
- **Phải rời tổ đội mới đổi khu** (server trả mã 3 `組隊不可換分區`). Vì vậy đổi khu luôn là flow
  "ra safe → rời PT → đổi → gom lại", KHÔNG phải teleport.
- **AUTO im lặng khi chưa có khu đủ chỗ** — cứ dò lại; chỉ **MANUAL** mới toast.
- **User ngoài (nếu bật ÁP DỤNG MỜI NGOÀI) là 1 thành viên của team**: khu phải đủ chỗ cho
  `số_acc + 1`; sau khi đủ bot leader mới **mời user ngoài + chờ** rồi mới vào sự kiện. Vòng dò lại
  (AUTO) / toast (MANUAL) áp dụng cho cả user ngoài.
- **Chỉ là nguồn lệnh duy nhất**: khi bật chính sách, `_dieu_phoi_chot_kenh` **không** chốt/gửi
  lệnh kênh nữa (`_event_channel_policy_active` → `return None`) để tránh 2 nguồn lệnh giằng nhau;
  picker (`do_channel_sync`) tự ghi `kenh_dich`.
- **Cùng 1 lượt**: leader đổi trước, member theo barrier (`channel_ready`) ngay sau đó.
- **Không đổi khu giữa trận** (`_kenh_doi_duoc_ngay`): đang `in_battle` / grace / đánh event.
- **Dropdown cập nhật live**: UI giữ tham chiếu Spinner/adapter; `setData` khi đang mở dropdown gọi
  `refreshOpenChannelDropdowns()` cập nhật số chỗ **tại chỗ** (không dựng lại View → popup không đóng).

## Kiểm chứng

```bash
python3 -B -m unittest discover -s tests -q -p 'test_android_safety.py'
```

Test liên quan: `test_event_channel_policy_roundtrip`, `test_event_channel_picker_auto_picks_emptiest`,
`test_event_channel_picker_manual_rejects_when_not_enough`, `test_ui_notice_queue`,
`test_event_channel_ui_wired`. Test online bắt buộc cho timing event thật (T2/T4/T6 20:00–22:00).
