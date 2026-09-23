#!/usr/bin/env bash
# Build APK ts_bot + kiem tra chu ky (khong de lot APK unsigned) + copy vao dist/.
# Dung:  bash scripts/build.sh [debug|release]     (mac dinh debug)
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT"

VARIANT="${1:-debug}"
case "$VARIANT" in
  debug)   TASK="assembleDebug" ;;
  release) TASK="assembleRelease" ;;
  *) echo "Variant khong hop le: $VARIANT (dung debug|release)"; exit 2 ;;
esac

echo "== ts_bot build :app:${TASK} (repo $ROOT) =="
./gradlew ":app:${TASK}" || { echo "BUILD THAT BAI"; exit 1; }

OUT_DIR="app/build/outputs/apk/${VARIANT}"
APK="$(ls -1 "$OUT_DIR"/*.apk 2>/dev/null | head -1)"
if [ -z "$APK" ]; then echo "Khong thay APK trong $OUT_DIR"; exit 1; fi
if printf '%s' "$APK" | grep -qi 'unsigned'; then
  echo "APK co ten chua 'unsigned' ($APK) -> KHONG dat. Kiem tra signingConfig."
  exit 1
fi

# apksigner: lay tu Android SDK (doc sdk.dir trong local.properties).
SDK="$(grep -E '^sdk.dir=' local.properties 2>/dev/null | cut -d= -f2-)"
APKSIGNER="$(ls -1 "$SDK"/build-tools/*/apksigner 2>/dev/null | sort -V | tail -1)"
if [ -n "$APKSIGNER" ] && [ -x "$APKSIGNER" ]; then
  echo "== Xac minh chu ky =="
  "$APKSIGNER" verify --print-certs "$APK" || { echo "APK KHONG duoc ky hop le (unsigned?)"; exit 1; }
else
  echo "(khong tim thay apksigner de xac minh)"
fi

mkdir -p dist
cp -f "$APK" dist/
echo "OK -> $APK"
echo "     -> dist/$(basename "$APK")"
