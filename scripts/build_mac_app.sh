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
    do shell script \"cd \" & quoted form of project_dir & \" && source .venv/bin/activate && transcribe serve --port 8000 > /dev/null 2>&1 &\"
    delay 1.5
    do shell script \"open http://localhost:8000\"
end run
"

osacompile -e "$APPLESCRIPT" -o "$APP_DIR"

echo "✅ Transcribe AI.app successfully generated at:"
echo "   $APP_DIR"
echo ""
echo "To run:"
echo "   open \"$APP_DIR\""
echo "Or drag '$APP_DIR' into your Mac's /Applications folder!"
