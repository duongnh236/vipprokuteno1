"""HTTP login -> lay user_id + access_token."""
import urllib.parse
import urllib.request
import urllib.error
import json
import time
import logging
from . import config

log = logging.getLogger("login")


import hashlib


# APP SECRET cua SDK game goc (`com.vtcmobile.gamesdk`): native lib `libsplay_native_keys.so`
# tra ve ban ro cua `NativeKeys.getPrivateKey()` = XOR 3 bang 32 byte nhung trong .so. Server giu
# CUNG gia tri nay de doi chieu `sign`. Doi key nay thi server tra `S:000-000` ma 3 "Chu ky khong
# hop le" -> khong dang nhap duoc (server doi cach ky tu ~01/10).
API_PRIVATE_KEY = "f94724205c8bc6d7ba2157c494708fe3"
SDK_VERSION = "102"


def _request_id_local_ms() -> str:
    """`requestId` giong SDK goc: Calendar.getTimeInMillis() + TimeZone.getDefault().getOffset(now).

    Server KHONG kiem moc thoi gian (da thu requestId=0 van vao duoc) - chi can khop trong chu ky.
    """
    now = time.time()
    try:
        off = time.altzone if time.localtime(now).tm_isdst and time.daylight else time.timezone
    except Exception:
        off = time.timezone
    return str(int(now * 1000) - int(off) * 1000)


def _login_sign(device_id: str, username: str, client_version: str, request_id: str) -> str:
    """`sign` = MD5(`requestId` + '.' + apiKey + '.' + deviceId + '.' + username + '.' +
    clientVersion + '.' + sdkVersion + '.' + privateKey) - giong `Utils.getSignDevice` cua SDK goc.
    """
    raw = "%s.%s.%s.%s.%s.%s.%s" % (
        request_id, config.API_KEY, device_id, username,
        client_version, SDK_VERSION, API_PRIVATE_KEY,
    )
    return hashlib.md5(raw.encode()).hexdigest()


class LoginError(RuntimeError):
    def __init__(self, data):
        self.data = data or {}
        self.error_code = self.data.get("error_code")
        super().__init__(f"Login that bai: {self.data}")

def _device_id_for(username: str) -> str:
    """Tao device_id DUY NHAT cho moi account (32 hex) - tranh server coi 2 acc chung device."""
    return hashlib.md5(("dev_" + username).encode()).hexdigest()


def _tracking_id_for(username: str) -> str:
    """tracking_id dang UUID duy nhat moi account."""
    h = hashlib.md5(("trk_" + username).encode()).hexdigest()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def login(username: str = None, password: str = None, device_id: str = None) -> dict:
    """Goi API login, tra ve {user_id, access_token, username}.

    Raise RuntimeError neu that bai.
    """
    username = username or config.USERNAME
    password = password or config.PASSWORD
    device_id = device_id or _device_id_for(username)

    client_version = "1.1"
    request_id = _request_id_local_ms()
    params = {
        "username": username,
        "password": password,
        "device_id": device_id,
        "agency_id": "1",
        "device_os_version": "Samsung SM-A528B 12",
        "client_version": client_version,
        "lang": "vi",
        "device_os": "android",
        "local_agency_id": "1",
        "tracking_id": _tracking_id_for(username),
        "carrier": "",
        # Server moi (tu ~01/10) doi `requestId` + `sign`; thieu/cu -> `error_code 3
        # "Chu ky khong hop le"` (ke ca khi dung tai khoan/mat khau).
        "sdk_version": SDK_VERSION,
        "requestId": request_id,
        "sign": _login_sign(device_id, username, client_version, request_id),
    }
    body = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(
        config.LOGIN_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "okhttp/4.12.0"},
    )
    # RETRY khi can cong ephemeral (WinError 10048: 100 acc login don dap -> cong TIME_WAIT chua
    # kip giai phong) hoac loi mang tam. Cho tang dan (cong tu giai phong sau ~120s TIME_WAIT).
    data = None
    last_err = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            break
        except (urllib.error.URLError, OSError) as e:
            last_err = e
            # WinError 10048 = address in use (can cong); 10055/10060 = het buffer/timeout -> deu retry duoc
            wait = min(30, 3 * (attempt + 1))
            log.warning("[%s] login loi (%s) -> thu lai sau %ds (lan %d/6)", username, e, wait, attempt + 1)
            time.sleep(wait)
    if data is None:
        raise RuntimeError(f"Login that bai sau 6 lan thu (can cong/loi mang): {last_err}")

    if not data.get("status"):
        raise LoginError(data)

    d = data["data"]
    return {
        "user_id": d["user_id"],
        "access_token": d["access_token"],
        "username": d["username"],
    }


if __name__ == "__main__":
    print(login())
