#!/usr/bin/env bash
# 验证前端构建产物能被后端挂载（单端口模式）
cd ~/disaster-viz || exit 1
nohup venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8012 > /tmp/uv3.log 2>&1 &
sleep 5

echo '--- GET / ---'
curl -s -m 10 http://127.0.0.1:8012/ | head -c 250
echo
echo '--- assets ---'
ls frontend/dist/assets
JSFILE=$(ls frontend/dist/assets/ | grep '\.js$' | head -1)
echo "js file: $JSFILE"
curl -s -m 10 -o /dev/null -w 'HTTP %{http_code} type=%{content_type} size=%{size_download}\n' "http://127.0.0.1:8012/assets/$JSFILE"

pkill -f 'port 8012' 2>/dev/null
exit 0
