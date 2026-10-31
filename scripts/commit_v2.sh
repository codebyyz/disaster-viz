#!/usr/bin/env bash
# 提交第二版改动并推送
set -e
cd ~/disaster-viz || exit 1

git add -A
git status -s

if git diff --cached --quiet; then
  echo "nothing to commit"
  exit 0
fi

git -c user.name="codebyyz" -c user.email="codebyyz@users.noreply.github.com" commit -m "feat(v2): 接入 NASA FIRMS 野火数据 + 前端数据源 tab 切换

- 新增 backend/firms.py：FIRMS area API adapter（路径式 URL + CSV 解析 + normalize）
- 新增 GET /fires：缺 MAP_KEY 返回 400，上游失败返回 502，不与地震接口耦合
- 前端 App.jsx 改为数据源驱动：地震/野火 tab 切换，复用同一张地图与统计条
- 野火按亮温 bright_ti4 着色，时间窗口适配 FIRMS 的 1-5 天上限
- 配置：.env.example / .gitignore 忽略 .env / compose 透传 FIRMS_MAP_KEY
- 文档：README 补 /fires APID 文档与第二版进度；smoke_test 增加野火降级检查"

echo "=== committed ==="
git log --oneline -3
