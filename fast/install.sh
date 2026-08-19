#!/usr/bin/env sh
# Fast Install & run - WSL, Linux, macOS
set -e

APP="https://github.com/TopSpeed0/Uv-Stremeio-Fast-ADD/archive/refs/heads/main.zip"

command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# When this script is itself piped into sh, our stdin is that pipe - and the console UI
# reads the keyboard from stdin. Hand it the real terminal back.
if [ -e /dev/tty ]; then
  uvx --refresh --from "$APP" stremio-fast-add </dev/tty
else
  uvx --refresh --from "$APP" stremio-fast-add
fi
