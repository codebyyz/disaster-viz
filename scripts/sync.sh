#!/usr/bin/env bash
# 把 Windows 工作区里编辑过的文件同步到 WSL 的 ~/disaster-viz
# 用法：bash /mnt/d/OpenClaw/workspace/projects/disaster-viz/scripts/sync.sh
set -euo pipefail

SRC=/mnt/d/OpenClaw/workspace/projects/disaster-viz
DST="$HOME/disaster-viz"

# 先检查换行符：在 Windows 上编辑的脚本若带 CRLF，在 WSL 里执行会报
# "$'\r': command not found"。写入时统一用 LF，这里只做提醒。
if grep -rlI $'\r' "$SRC/scripts" 2>/dev/null; then
  echo "[WARN] 上面这些脚本含 CRLF，执行前先 dos2unix"
fi

FILES=(
  backend/main.py
  backend/web.py
  backend/db.py
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
  scripts/smoke_test.py
  scripts/probe_routes.py
  scripts/debug_mount.sh
  scripts/git_commit_w3.sh
  scripts/push.sh
  scripts/check-proxy.ps1
  README.md
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
