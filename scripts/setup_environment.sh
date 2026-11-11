#!/usr/bin/env bash
set -euo pipefail

# Lublin Anno Domini 1392: Environment & Toolchain Setup
echo "=== Checking Lublin 1392 Environment ==="

# 1. Check Node & NPM dependencies
if [ ! -d "node_modules" ]; then
  echo "Installing Node.js dependencies..."
  npm install
else
  echo "Node.js dependencies already installed."
fi

# 2. Check Blender 3.6 LTS
BLENDER_DIR="/home/antigravity/blender"
BLENDER_BIN="$BLENDER_DIR/blender"

if [ ! -x "$BLENDER_BIN" ]; then
  echo "Installing portable Blender 3.6 LTS to $BLENDER_DIR..."
  mkdir -p "$BLENDER_DIR"
  curl -sSL https://download.blender.org/release/Blender3.6/blender-3.6.18-linux-x64.tar.xz | tar -xJ -C "$BLENDER_DIR" --strip-components=1
fi

echo "Blender version:"
"$BLENDER_BIN" --version | head -n 1

# 3. Add to user PATH if not present
mkdir -p "$HOME/.local/bin"
ln -sf "$BLENDER_BIN" "$HOME/.local/bin/blender"

echo "=== Environment Setup Complete ==="
