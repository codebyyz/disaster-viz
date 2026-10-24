#!/usr/bin/env bash
# 提交 W3 改动。用法：bash scripts/git_commit_w3.sh
set -uo pipefail
cd "$HOME/disaster-viz" || exit 1

git add -A
git status --short
echo "--- committing ---"
git commit -m "feat: W3 交互筛选 + Docker 化

后端
- main.py 移入 backend/，为 W4 的 db / adapters 预留目录结构
- 新增 /health 存活探测（Docker healthcheck 用）
- /earthquakes 支持 days / max_magnitude，筛选下沉到 USGS 数据源端
- 抽取 normalize()，统一 USGS feature 到前端/落库的字段
- 根路径返回构建好的前端页面，静态资源挂 /assets

前端
- 时间窗口（24h/7d/30d/90d）+ 最小震级筛选
- 统计条：最强震、平均震源深度
- 弹窗加 USGS 详情外链，选中点高亮
- 改用相对路径 + Vite proxy，开发与容器同源，消除 CORS 依赖
- AbortController 取消过期请求，避免切换筛选时的竞态

容器
- 多阶段 Dockerfile：node 构建前端 -> python slim 运行，非 root 用户
- docker compose 单命令启动，:8000 同时提供页面与 API

工具
- scripts/sync.sh / dev_restart.sh / smoke_test.py / net_check.py
- docs/w3-interaction-and-docker.md 记录决策与踩坑"
echo "--- log ---"
git log --oneline -3
