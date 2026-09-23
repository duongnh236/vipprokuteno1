---
name: Build APK
description: Dùng khi build/chạy release APK của ts_bot — version tự tăng mỗi build qua version.properties, ký APK (tránh lỗi unsigned), tên file output, xác minh chữ ký, splash hiển thị version, và cập nhật GitHub Release cho updater.
---

# Build APK

Build một APK cho `com.fen.tsbot`. **Version tự tăng mỗi lần build**, APK **luôn được ký** (không
dính "unsigned"), và có **splash hiển thị số phiên bản**.

## Version tự tăng

- Nguồn sự thật: **`version.properties`** (root repo), chỉ 1 dòng `VERSION_CODE=148`.
- `app/build.gradle` đọc file lúc **configuration** → `versionCode = VERSION_CODE`,
  `versionName = "v" + VERSION_CODE`.
- Mỗi lần chạy `assembleDebug`/`assembleRelease`, task **`bumpVersion`** tự cộng `VERSION_CODE` lên
  1 và ghi lại file → **lần build sau dùng số lớn hơn**.
  - Vì đọc ở bước configuration nên **APK của lần build hiện tại vẫn mang số cũ**, còn file ghi số
    cho lần sau. Ví dụ file đang `148` → build ra `v148`, file thành `149` → build sau ra `v149`.
- Muốn mốc lại: sửa tay `version.properties` (vd về `148`) rồi build.
- `versionName` **phải khớp tag Release GitHub** (`vNNN`) vì `UpdateManager` so `versionCode` với
  `versionCodeFromTag(tag)`.

## Ký APK (tránh unsigned)

- `signingConfigs.debug` bật `enableV1Signing` + `enableV2Signing`; **cả `release` dùng
  `signingConfig signingConfigs.debug`**, nên APK release **được ký** (không phải
  `app-release-unsigned.apk`).
- Lý do giữ debug certificate: các bản đã phát hành trước đây dùng nó → Android cho cập nhật đè mà
  không phải gỡ app; ký v1+v2 để ROM cũ không báo nhầm "unsigned".
- Tên file output **không chứa "unsigned"**:
  `aTSBot-Android-v<version>-<buildType>.apk` (đặt trong `androidComponents.onVariants`).
  Updater GitHub bỏ qua asset có tên chứa "unsigned" → tên này an toàn.
- **Kiểm tra sau build** bằng `apksigner verify --print-certs <apk>`.
- LƯU Ý khi xem chữ ký: `apksigner verify -v` (không truyền gì) lấy `minSdk` của APK (26) nên báo
  `Verified using v1 scheme: false` mặc dù APK **có** `META-INF/CERT.SF` + `CERT.RSA`. Muốn xác
  nhận v1 thật, ép min-sdk thấp:
  ```bash
  apksigner verify -v --min-sdk-version 21 <apk>   # -> v1: true, v2: true
  ```

## Build

```bash
./gradlew :app:assembleDebug     # APK debug (ký bằng debug key)
./gradlew :app:assembleRelease   # APK release (ký bằng debug key, minify off)
```

Hoặc dùng script (build + verify + copy vào `dist/`):

```bash
bash .opencode/skills/apk-build/scripts/build.sh debug
bash .opencode/skills/apk-build/scripts/build.sh release
```

Output:
```
app/build/outputs/apk/<variant>/aTSBot-Android-v<version>-<variant>.apk
dist/aTSBot-Android-v<version>-<variant>.apk        # do script copy
```

## Splash

- `.SplashActivity` là LAUNCHER (không phải `MainActivity`); hiện logo + tên + **`BuildConfig.VERSION_NAME`**,
  sau ~1.4s chuyển sang `MainActivity`.
- Layout: `res/layout/activity_splash.xml`; chuỗi `app_name` ở `res/values/strings.xml`.
- Nhờ `buildConfig true`, splash luôn hiện đúng version của bản đang chạy (vì version auto-bump).

## Cập nhật GitHub Release (cho updater)

1. Build xong, xác minh chữ ký.
2. Tạo tag/release **đúng dạng `vNNN`** khớp `versionCode` (vd APK `v149` → tag `v149`).
3. Đính kèm **file APK đã ký**, tên **không chứa "unsigned"**.
4. Updater (`UpdateManager`) tải release mới nhất, so `versionCode`; tên asset chứa "unsigned" sẽ bị
   bỏ qua, và APK trong release phải có `versionCode` khớp tag.

## Lỗi thường gặp

| Triệu chứng | Nguyên nhân / cách xử lý |
| --- | --- |
| Tên APK có `unsigned` | build type thiếu `signingConfig` → đặt `signingConfig signingConfigs.debug` |
| Cài đè báo "App not installed" | ký khác key bản đang cài, HOẶC `versionCode` thấp hơn bản đang cài |
| Updater không thấy bản mới | tag không khớp `versionCode`, hoặc asset tên chứa "unsigned", hoặc versionCode không tăng |
| ROM báo "unsigned" dù đã ký | thiếu v1 signing → bật `enableV1Signing true` |
| `version.properties` không đổi | task `bumpVersion` chỉ gắn vào `assembleDebug`/`assembleRelease` |

## Kiểm chứng nhanh

```bash
# version cua APK vua build
"$ANDROID_HOME"/build-tools/*/aapt dump badging <apk> | head -1     # package + versionName
"$ANDROID_HOME"/build-tools/*/apksigner verify --print-certs <apk>   # phai co chu ky, khong unsigned
"$ANDROID_HOME"/build-tools/*/apksigner verify -v --min-sdk-version 21 <apk>   # xac nhan ca v1 + v2
```
