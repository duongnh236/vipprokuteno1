"""Bounded S2C trace for Android debugging; never records outgoing credentials.

GHI BAT DONG BO: truoc day `record()` tao dict + json.dumps + ghi file + flush() NGAY tren
luong recv -> MOI packet S2C la mot lan cham dia, chan luong nhan (turn danh 0x35 bi xep hang
sau I/O). Nay `record()` chi day mot ban ghi THO vao hang doi (put_nowait, khong format, khong
I/O); mot thread nen lo hex/json/ghi file theo lo. `snapshot()` doi hang doi xuong het roi doc.
"""
import json
import logging
import os
import queue
import threading
import time
from logging.handlers import RotatingFileHandler

_lock = threading.RLock()
_start_lock = threading.Lock()
_handler = None
_writer_started = False

# Hang doi ban ghi THO: (ts, username, opcode, packet_bytes). Gioi han de khong phinh RAM khi
# server day nhanh hon dia; day thi BO (trace la debug, khong duoc lam nghen game).
_MAX_PENDING = 8192
_queue = queue.Queue(maxsize=_MAX_PENDING)


def _path():
    from ._appdir import app_dir
    return os.path.join(app_dir(), "server_packets.jsonl")


def _get_handler_locked():
    global _handler
    if _handler is None:
        _handler = RotatingFileHandler(_path(), maxBytes=4 * 1024 * 1024,
                                       backupCount=2, encoding="utf-8")
        _handler.setFormatter(logging.Formatter("%(message)s"))
    return _handler


def _row(item):
    ts, username, opcode, packet = item
    # Login/server transfer may contain access credentials. Preserve metadata only.
    redacted = int(opcode) == 0x01
    return {"timestamp": ts, "direction": "S2C", "account": str(username),
            "opcode": "0x%02X" % opcode, "length": len(packet),
            "redacted": redacted, "payload_hex": None if redacted else packet[7:].hex(),
            "frame_hex": None if redacted else packet.hex(),
            "format": "decrypted protocol frame; unknown fields not guessed"}


def _write_batch(batch):
    with _lock:
        handler = _get_handler_locked()
        for item in batch:
            try:
                handler.emit(logging.LogRecord("packet_trace", logging.INFO, "", 0,
                                               json.dumps(_row(item), ensure_ascii=False),
                                               (), None))
            except Exception:
                # Debug trace must never interrupt game packet handling.
                pass
        # Flush MOT lan cho ca lo thay vi tung ban ghi -> giam han so lan cham dia.
        try:
            handler.flush()
        except Exception:
            pass


def _writer_loop():
    while True:
        item = _queue.get()
        batch = [item]
        while len(batch) < 256:
            try:
                batch.append(_queue.get_nowait())
            except queue.Empty:
                break
        try:
            _write_batch(batch)
        except Exception:
            pass
        finally:
            for _ in batch:
                try:
                    _queue.task_done()
                except ValueError:
                    pass


def _ensure_writer():
    global _writer_started
    if _writer_started:
        return
    with _start_lock:
        if _writer_started:
            return
        threading.Thread(target=_writer_loop, name="packet-trace", daemon=True).start()
        _writer_started = True


def record(username, opcode, packet):
    try:
        _queue.put_nowait((time.time(), str(username), int(opcode), packet))
    except queue.Full:
        pass
    _ensure_writer()


def _wait_idle(timeout=2.0):
    """Cho writer xu ly het ban ghi da xep hang (dung truoc khi doc file cho snapshot)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _queue.unfinished_tasks == 0:
            return True
        time.sleep(0.01)
    return False


def snapshot(limit=100):
    limit = max(1, min(200, int(limit)))
    _wait_idle()
    with _lock:
        if _handler is not None:
            _handler.flush()
        path = _path()
        if not os.path.exists(path):
            return {"packets": [], "note": "Chua nhan packet trong ban capture nay"}
        with open(path, "rb") as stream:
            stream.seek(0, 2)
            start = max(0, stream.tell() - 512 * 1024)
            stream.seek(start)
            raw = stream.read()
        lines = raw.decode("utf-8", errors="replace").splitlines()
        if start:
            lines = lines[1:]
        rows = []
        for line in lines[-limit:]:
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
        return {"packets": rows, "note": "Preview toi da 200 packet. File JSONL xoay vong 12MB; opcode 0x01 an thong tin xac thuc."}
