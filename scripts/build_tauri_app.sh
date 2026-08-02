#!/usr/bin/env bash

# Tauri v2 Desktop Build & Launch Script for Transcribe AI

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_DIR"

echo "🦀 Building Transcribe AI with Tauri v2 (Cross-Platform)..."

# Ensure Rust & Cargo are installed
if ! command -v cargo &> /dev/null; then
    echo "❌ Rust/Cargo is not installed. Please install Rust from https://rustup.rs"
    echo "   Command: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
    exit 1
fi

# Ensure Node/npx or cargo-tauri is available
if command -v npx &> /dev/null; then
    echo "🚀 Launching Tauri v2 Desktop App via npx..."
    npx -y @tauri-apps/cli@v2 dev
elif cargo tauri --version &> /dev/null; then
    echo "🚀 Launching Tauri v2 Desktop App via cargo-tauri..."
    cargo tauri dev
else
    echo "📦 Installing Tauri v2 CLI..."
    cargo install tauri-cli --version "^2.0.0"
    cargo tauri dev
fi
