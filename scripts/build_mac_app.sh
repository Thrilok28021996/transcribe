#!/usr/bin/env bash

# Build Native macOS Application Bundle for Transcribe AI

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
APP_DIR="$PROJECT_DIR/dist/Transcribe AI.app"

echo "🔨 Building Transcribe AI for macOS..."

mkdir -p "$PROJECT_DIR/dist"
rm -rf "$APP_DIR"

# Use osacompile to create native macOS App bundle
APPLESCRIPT="
on run
    set project_dir to \"$PROJECT_DIR\"
    do shell script \"export PATH=\\\"\$HOME/.local/bin:\$HOME/Library/Python/3.14/bin:/opt/homebrew/bin:/usr/local/bin:\$PATH\\\"; cd \" & quoted form of project_dir & \" && (source .venv/bin/activate 2>/dev/null || true) && (transcribe serve --port 8000 > /tmp/transcribe_app.log 2>&1 &)\"
    delay 1.5
    do shell script \"open http://localhost:8000\"
end run
"

osacompile -e "$APPLESCRIPT" -o "$APP_DIR"

if [ -f "$PROJECT_DIR/src-tauri/icons/icon.icns" ]; then
    cp "$PROJECT_DIR/src-tauri/icons/icon.icns" "$APP_DIR/Contents/Resources/applet.icns"
    cp "$PROJECT_DIR/src-tauri/icons/icon.icns" "$APP_DIR/Contents/Resources/droplet.icns" 2>/dev/null || true
fi

# Ensure Info.plist has NSMicrophoneUsageDescription
PLIST="$APP_DIR/Contents/Info.plist"
if [ -f "$PLIST" ]; then
    /usr/libexec/PlistBuddy -c "Add :NSMicrophoneUsageDescription string 'Transcribe AI requires access to your microphone to capture live speech and transcribe meeting notes locally.'" "$PLIST" 2>/dev/null || \
    /usr/libexec/PlistBuddy -c "Set :NSMicrophoneUsageDescription 'Transcribe AI requires access to your microphone to capture live speech and transcribe meeting notes locally.'" "$PLIST" 2>/dev/null || true
fi

# Ad-hoc sign app bundle with microphone entitlements
if command -v codesign &> /dev/null && [ -f "$PROJECT_DIR/src-tauri/Entitlements.plist" ]; then
    codesign --force --deep --options runtime --entitlements "$PROJECT_DIR/src-tauri/Entitlements.plist" -s - "$APP_DIR" 2>/dev/null || true
fi
touch "$APP_DIR"


# Install CLI symlink to ~/.local/bin/transcribe
mkdir -p "$HOME/.local/bin"
rm -f "$HOME/.local/bin/transcribe"
ln -s "$PROJECT_DIR/.venv/bin/transcribe" "$HOME/.local/bin/transcribe" 2>/dev/null || true

echo "✅ Transcribe AI.app successfully generated at:"
echo "   $APP_DIR"
echo "✅ 'transcribe' CLI command linked to:"
echo "   $HOME/.local/bin/transcribe"
echo ""
echo "To run App:"
echo "   open \"$APP_DIR\""
echo "To run CLI:"
echo "   transcribe record --mode mixed"

