#!/usr/bin/env bash
# 排查静态前端是否被挂载
set -uo pipefail
cd "$HOME/disaster-viz" || exit 1
source venv/bin/activate

python - <<'PY'
from backend.web import DIST_DIR, mount_frontend
from backend.main import FRONTEND_MOUNTED, app

print("DIST_DIR       :", DIST_DIR)
print("index exists   :", (DIST_DIR / "index.html").exists())
print("mounted        :", FRONTEND_MOUNTED)
print("routes         :", [(getattr(r, 'path', None), getattr(r, 'name', None)) for r in app.routes])
PY
