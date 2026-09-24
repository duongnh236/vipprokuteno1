#!/usr/bin/env bash
# Kiểm chứng logic luồng Dị Giới -> Train của ts_bot.
# Chạy được từ bất kỳ thư mục nào.
#
# LƯU Ý: test_android_safety hiện có 1 fail CÓ SẴN TỪ TRƯỚC (không liên quan luồng này):
#   test_navigation_never_counts_a_move_rejected_by_combat
#   -> chờ `MOVE_XA_TOI_DA` / `self._move_chia_doan(x, y)` trong navigate_to (đang làm dở).
# Script bỏ qua đúng fail đó; mọi fail KHÁC vẫn làm script trả mã lỗi.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT"

KNOWN_WIP="test_navigation_never_counts_a_move_rejected_by_combat"

echo "== ts_bot: kiểm chứng DG -> Train (repo: $ROOT) =="

fail=0
for t in test_android_safety test_workflow_architecture test_channel_regroup test_city_exit; do
  out="$(python3 -B -m unittest discover -s tests -q -p "${t}.py" 2>&1)"
  rc=$?
  if [ "$rc" -eq 0 ]; then
    echo "-- $t: OK"
    continue
  fi
  # grep -c (doc het input, khong thoat som -> tranh SIGPIPE voi pipefail).
  n_fail="$(printf '%s\n' "$out" | grep -cE '^(FAIL|ERROR):')"
  n_wip="$(printf '%s\n' "$out" | grep -c "$KNOWN_WIP")"
  if [ "$t" = "test_android_safety" ] && [ "${n_wip:-0}" -ge 1 ] && [ "${n_fail:-0}" -le 1 ]; then
    echo "-- $t: chỉ fail test WIP đã biết ($KNOWN_WIP) -> bỏ qua"
    continue
  fi
  echo "-- $t: FAIL"
  printf '%s\n' "$out" | grep -E '^(FAIL|ERROR):|^(Ran |OK|FAILED)' | head -n 20
  fail=1
done

if [ "$fail" -ne 0 ]; then
  echo "KẾT QUẢ: CÓ fail ngoài danh sách WIP -> cần xem lại."
  exit 1
fi
echo "KẾT QUẢ: OK (kiểm thử logic). Vẫn phải chạy 1 lượt test online trước khi release."
echo "Toàn bộ suite (khi cần): python3 -B -m unittest discover -s tests -q"
