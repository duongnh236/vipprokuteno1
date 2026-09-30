"""Hang doi THONG BAO Python -> UI Android (toast) cho cac su kien luong chay.

Vi sao can: vai su co CHI XAY RA GIUA LUONG tu dong (vd phan khu 40NPC user chon khong
du cho ca team sau khi nguoi khac tran vao). Luc do khong co nut nao de tra ket qua, nen
phai co kenh rieng de day thong bao len UI. Android poll `agent_bridge.poll_ui_notices_json`
trong vong dashboard 2.5s va hien Toast cho ban ghi MOI.

Gon, thread-safe, khong I/O, khong phu thuoc Android -> test duoc bang unittest.
"""
import threading
import time

_lock = threading.Lock()
_seq = 0
_items = []          # [{"seq": n, "message": str, "at": ts}]
_MAX = 30            # giu hang doi ngan; ban ghi cu bi bo khi tran


def push(message):
    """Them 1 thong bao. Tra ve seq (int) hoac None neu message rong."""
    global _seq
    msg = str(message or "").strip()
    if not msg:
        return None
    with _lock:
        _seq += 1
        seq = _seq
        _items.append({"seq": seq, "message": msg, "at": time.time()})
        if len(_items) > _MAX:
            del _items[:len(_items) - _MAX]
    return seq


def poll(after=0):
    """Tra cac thong bao co seq > `after` (khong xoa). Kem `seq` lon nhat de UI nho moc."""
    try:
        after = int(after or 0)
    except Exception:
        after = 0
    with _lock:
        rows = [dict(x) for x in _items if int(x["seq"]) > after]
        last = _seq
    return {"seq": last, "notices": rows}


def clear():
    """Xoa sach (dung cho test)."""
    global _seq
    with _lock:
        _items.clear()
        _seq = 0
