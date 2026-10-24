#!/usr/bin/env bash
# 把 Windows 工作区里编辑过的文件同步到 WSL 的 ~/disaster-viz
# 用法：bash /mnt/d/OpenClaw/workspace/projects/disaster-viz/scripts/sync.sh
set -euo pipefail

SRC=/mnt/d/OpenClaw/workspace/projects/disaster-viz
DST="$HOME/disaster-viz"

FILES=(
  backend/main.py
  backend/web.py
  backend/__init__.py
  frontend/src/App.jsx
  frontend/src/App.css
  frontend/vite.config.js
  Dockerfile
  docker-compose.yml
  .gitignore
  .dockerignore
  requirements.txt
  scripts/net_check.py
)

mkdir -p "$DST/backend" "$DST/frontend/src" "$DST/scripts"
for f in "${FILES[@]}"; do
  if [ -f "$SRC/$f" ]; then
    cp "$SRC/$f" "$DST/$f"
    echo "synced $f"
  fi
done

if [ -d "$SRC/docs" ]; then
  mkdir -p "$DST/docs"
  cp "$SRC"/docs/*.md "$DST/docs/" 2>/dev/null || true
  echo "synced docs/"
fi
