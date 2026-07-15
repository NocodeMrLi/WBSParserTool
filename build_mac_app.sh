#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR=".venv-mac"
APP_NAME="WBSParserTool"
ICON_SOURCE="assets/app_icon_masked_source.png"
ICON_FALLBACK="assets/app_icon_preview.png"
ICON_ICNS="assets/app_icon.icns"
ICONSET_DIR="build/macos/AppIcon.iconset"
SPEC_DIR="build/macos/spec"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r requirements.txt

if [[ ! -f "$ICON_ICNS" ]]; then
  if [[ ! -f "$ICON_SOURCE" ]]; then
    ICON_SOURCE="$ICON_FALLBACK"
  fi

  if [[ ! -f "$ICON_SOURCE" ]]; then
    echo "Icon source not found: assets/app_icon_masked_source.png or assets/app_icon_preview.png"
    exit 1
  fi

  rm -rf "$ICONSET_DIR"
  mkdir -p "$ICONSET_DIR"

  sips -z 16 16 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_16x16.png" >/dev/null
  sips -z 32 32 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_16x16@2x.png" >/dev/null
  sips -z 32 32 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_32x32.png" >/dev/null
  sips -z 64 64 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_32x32@2x.png" >/dev/null
  sips -z 128 128 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_128x128.png" >/dev/null
  sips -z 256 256 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
  sips -z 256 256 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_256x256.png" >/dev/null
  sips -z 512 512 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
  sips -z 512 512 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_512x512.png" >/dev/null
  sips -z 1024 1024 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_512x512@2x.png" >/dev/null

  iconutil -c icns "$ICONSET_DIR" -o "$ICON_ICNS"
fi

"$VENV_DIR/bin/pyinstaller" \
  --noconfirm \
  --clean \
  --windowed \
  --specpath "$SPEC_DIR" \
  --name "$APP_NAME" \
  --icon "$PROJECT_ROOT/$ICON_ICNS" \
  --osx-bundle-identifier "com.mrli.wbsparsertool" \
  --hidden-import "ui.macos_window" \
  --add-data "$PROJECT_ROOT/prompts:prompts" \
  --add-data "$PROJECT_ROOT/assets:assets" \
  "$PROJECT_ROOT/app.py"

PLIST_PATH="dist/$APP_NAME.app/Contents/Info.plist"
if [[ -f "$PLIST_PATH" ]]; then
  /usr/libexec/PlistBuddy -c "Delete :NSRequiresAquaSystemAppearance" "$PLIST_PATH" >/dev/null 2>&1 || true
  /usr/libexec/PlistBuddy -c "Add :NSRequiresAquaSystemAppearance bool true" "$PLIST_PATH"
fi

echo ""
echo "Build complete: $PROJECT_ROOT/dist/$APP_NAME.app"
