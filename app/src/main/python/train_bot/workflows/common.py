"""Common workflow implementation; explicit dependencies, no runner imports.

Moved without changing the existing game protocol/route algorithms.
"""


def _workflow_leave_current_area(c, stopped_fn, *, services):
    """Finish battle, stop DG movement and release farm party before a city teleport."""
    time = services.time
    c.stop_run_around()
    c._dg_pursuit_paused = True
    c.set_party_invite_ready(False)
    # TẬP KẾT VỀ THÀNH: phải tắt Hộp Máy trước khi chờ hết trận. Nếu chỉ chờ combat
    # clear, acc vừa hết trận sẽ bị quái kéo vào trận kế tiếp trước khe teleport (log thật:
    # manual_route_city_arrived đứng 0/5 suốt 150s trên map 23802). Đánh dấu thời điểm gửi
    # pause để ACK S:065-002 không bị handler hiểu nhầm là server tự tắt rồi bật lại ngay.
    # GIU flee_mode=True suot luc cho het tran -> khong tai aggro giua ket tran va teleport.
    c.flee_mode = True
    try:
        has_pause_state = hasattr(c, "_machinebox_server_paused")
        c._machinebox_force_paused = True
        c._machinebox_server_paused = False
        c._machinebox_pause_sent_at = time.time()
        send = getattr(c, "send", None)
        if callable(send):
            send(0x41, b"\x02\x00")
    except OSError:
        pass
    # CHO HET TRAN de teleport (server chan tele khi dang danh). O bai quai, acc co the bi keo tran
    # LIEN TUC -> phai KIEN TRI (flee + cho) chu KHONG bo sau 1 lan. Truoc day `_wait_combat_clear`
    # xong la `raise` ngay neu con combat -> 2 acc ket o bai, khong ve thanh cung leader (log 22/09
    # 11:23: sevarb40 + XeTai "Chua het tran/da dung; khong teleport").
    _deadline = time.time() + 240.0
    while True:
        c._wait_combat_clear(idle=2.0, cap=120.0)
        if stopped_fn():
            raise RuntimeError("Đã dừng; không teleport")
        if not c.in_combat(idle_secs=2.0):
            break
        if time.time() >= _deadline:
            raise RuntimeError("Chưa hết trận/đã dừng; không teleport")
        c.flee_mode = True
        time.sleep(2.0)
    # Teleport gui truoc ACK pause thuong bi server im lang. ACK thuc te co the cham
    # 12-20s, nen doi trang thai server thay vi doan bang cua so 10s.
    if has_pause_state:
        deadline = time.time() + 20.0
        while (not c._machinebox_server_paused and c.running
               and not stopped_fn() and time.time() < deadline):
            time.sleep(0.2)
    if c.in_di_gioi():
        c.exit_di_gioi()
        if stopped_fn() or c.in_di_gioi():
            raise RuntimeError("Chưa được server xác nhận thoát Dị giới")
    if c.party_members or (c.party_leader and c.party_leader != c.self_entity):
        c.leave_party()
        deadline = time.time() + 15
        while c.party_members or (c.party_leader and c.party_leader != c.self_entity):
            if stopped_fn() or time.time() > deadline:
                raise RuntimeError("Server chưa xác nhận rời party farm")
            time.sleep(0.5)
    # Giữ flee cho tới lúc teleport/tập kết xong. Nhánh lập party/ra bãi sẽ gọi
    # combat_ready() rồi tắt flee đúng lúc, tránh tái aggro giữa hai thao tác.
    c.flee_mode = True
